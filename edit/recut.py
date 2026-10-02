#!/usr/bin/env python3
"""Re-cut the ANTIDOTE film from its current export, driven by edl.json.

  python edit/recut.py detect input.mp4               # print the real cut points
  python edit/recut.py render input.mp4 out.mp4       # render the new edit
  python edit/recut.py render input.mp4 out.mp4 --snap  # ...with cuts snapped to the beat

The picture is re-ordered, but the original music runs underneath unchanged,
so there are no audio seams. Needs ffmpeg on PATH (or `pip install imageio-ffmpeg`).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found: install it or `pip install imageio-ffmpeg`")


FFMPEG = ffmpeg_exe()


def probe(path):
    """Width, height, fps, duration and audio presence, parsed from `ffmpeg -i`."""
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    video = re.search(r"Stream #.*Video:.*?(\d{2,5})x(\d{2,5})", err)
    fps = re.search(r"([\d.]+) fps", err)
    return {
        "duration": int(h) * 3600 + int(m) * 60 + float(s),
        "width": int(video.group(1)),
        "height": int(video.group(2)),
        "fps": float(fps.group(1)) if fps else 30.0,
        "audio": "Audio:" in err,
    }


def detect(path, threshold):
    """Print every hard cut in the export so edl.json in/out points can be checked."""
    err = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path), "-an",
         "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    cuts = [float(t) for t in re.findall(r"pts_time:([\d.]+)", err)]
    bounds = [0.0] + cuts + [probe(path)["duration"]]
    for i, (a, b) in enumerate(zip(bounds, bounds[1:]), 1):
        print(f"shot {i:2d}  {a:6.2f} -> {b:6.2f}  ({b - a:4.2f}s)")


def beat_times(path, sr=22050, hop=512):
    """Rough beat grid: spectral-flux onsets, tempo by autocorrelation, best phase."""
    import numpy as np
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-vn", "-ac", "1",
                          "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    y = np.frombuffer(raw, dtype=np.float32)
    n_fft = 2048
    frames = np.lib.stride_tricks.sliding_window_view(y, n_fft)[::hop] * np.hanning(n_fft)
    mag = np.log1p(np.abs(np.fft.rfft(frames, axis=1)))
    env = np.maximum(np.diff(mag, axis=0), 0).sum(axis=1)
    env = (env - env.mean()) / (env.std() + 1e-9)
    fps = sr / hop

    lags = np.arange(int(fps * 60 / 180), int(fps * 60 / 70) + 1)
    ac = np.array([np.dot(env[:-lag], env[lag:]) for lag in lags])
    period = lags[ac.argmax()]
    phase = max(range(period), key=lambda p: env[p::period].sum())
    print(f"tempo ~{60 * fps / period:.1f} BPM")
    return (np.arange(phase, len(env), period) + 1) / fps


def timeline(clips):
    """Start time of each clip on the output timeline, and the total length."""
    starts, t = [], 0.0
    for i, c in enumerate(clips):
        if i:
            t -= c.get("transition", {}).get("dur", 0.0)
        starts.append(t)
        t += c["dur"]
    return starts, t


def snap_to_beats(clips, beats, min_dur=0.4):
    """Move each internal cut to the nearest beat, keeping the total length fixed."""
    import numpy as np
    starts, total = timeline(clips)
    period = float(np.median(np.diff(beats)))
    new = [0.0]
    for i, s in enumerate(starts[1:], 1):
        b = beats[np.abs(beats - s).argmin()]
        s = b if abs(b - s) < 0.35 * period else s
        new.append(max(s, new[-1] + min_dur))
    new.append(total)
    for i, c in enumerate(clips):
        overlap = clips[i + 1].get("transition", {}).get("dur", 0.0) if i + 1 < len(clips) else 0.0
        c["dur"] = round(new[i + 1] - new[i] + overlap, 3)
    return clips


def zoom_expr(c, fx):
    """Per-frame zoom factor: a slow push from push[0] to push[1], times a decaying punch-in."""
    z0, z1 = fx.get("push", (1.0, 1.0))
    expr = f"({z0}+{z1 - z0}*t/{c['dur']})"
    if "punch" in fx:
        amp, frames = fx["punch"]
        expr += f"*(1+{amp}*max(0,1-t*{fx['fps']}/{frames}))"
    return expr


def build_filter(clips, w, h, fps, fade_in):
    parts = []
    for i, c in enumerate(clips):
        speed = c["dur"] / (c["out"] - c["in"])
        fx = dict(c.get("fx", {}), fps=fps)
        retime = (f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
                  if fx.get("smooth") else f"fps={fps}")
        chain = (f"[{c.get('input', 0)}:v]trim=start={c['in']}:end={c['out']},"
                 f"setpts=(PTS-STARTPTS)*{speed:.5f},{retime},"
                 f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                 f"setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=1,"
                 f"trim=duration={c['dur']},setpts=PTS-STARTPTS")
        for lut in fx.get("luts", []):
            chain += f",lut3d=file='{lut}'"
        if "push" in fx or "punch" in fx:
            z = zoom_expr(c, fx)
            chain += (f",scale=w='trunc({w}*{z}/2)*2':h='trunc({h}*{z}/2)*2':eval=frame,"
                      f"crop={w}:{h},setsar=1")
        if "flash" in fx:
            chain += f",fade=t=in:st=0:d={fx['flash'] / fps:.4f}:color=white"
        if i == 0 and fade_in:
            chain += f",fade=t=in:d={fade_in}"
        parts.append(chain + f",fps={fps}[v{i}]")

    cur, length = "v0", clips[0]["dur"]
    for i, c in enumerate(clips[1:], 1):
        out = f"x{i}"
        tr = c.get("transition")
        if tr:
            parts.append(f"[{cur}][v{i}]xfade=transition={tr['type']}:duration={tr['dur']}:"
                         f"offset={length - tr['dur']:.3f}[{out}]")
            length += c["dur"] - tr["dur"]
        else:
            parts.append(f"[{cur}][v{i}]concat=n=2:v=1:a=0,fps={fps}[{out}]")
            length += c["dur"]
        cur = out
    return ";".join(parts), cur, length


def finish_chain(opts, w, h):
    """Whole-film finishing: camera shake windows (frames), vignette and film grain."""
    steps = []
    shakes = opts.get("shake", [])
    if shakes:
        margin = max(amp for _, _, amp in shakes)
        off = "+".join(f"if(between(n,{a},{b}),{amp}*sin(n*{1.9 + k}){'*'}({b}-n)/{b - a},0)"
                       for k, (a, b, amp) in enumerate(shakes))
        steps.append(f"scale={w + 2 * margin}:-2,crop={w}:{h}:x='{margin}+{off}':"
                     f"y='{margin}+{off.replace('sin', 'cos')}'")
    if opts.get("vignette"):
        steps.append(f"vignette=angle={opts['vignette']}")
    if opts.get("grain"):
        steps.append(f"noise=c0s={opts['grain']}:c0f=t+u")
    return ",".join(steps)


def from_frames(edl):
    """Edit lists with "units": "frames" give in/out/dur and transitions in frames."""
    fps = edl["output"]["fps"]
    for c in edl["clips"]:
        c["in"] = c["in"] / fps - 0.01
        c["out"] = c["out"] / fps - 0.01
        c["dur"] = c["dur"] / fps
        if "transition" in c:
            c["transition"]["dur"] /= fps


def render(src, dst, edl_path, snap):
    """src is the video to re-cut, or the media folder when the edit list names its sources."""
    edl = json.loads(Path(edl_path).read_text())
    if edl.get("units") == "frames":
        from_frames(edl)
    clips, opts = edl["clips"], edl.get("output", {})

    sources = edl.get("sources")
    files = [Path(src) / f for f in sources.values()] if sources else [Path(src)]
    index = {name: i for i, name in enumerate(sources or [])}
    infos = [probe(f) for f in files]
    for c in clips:
        c["input"] = index.get(c.get("src"), 0)
        if c["out"] > infos[c["input"]]["duration"] + 0.05:
            sys.exit(f"{c['shot']}: out {c['out']:.2f} is past the end of its source")

    music = Path(src) / edl["music"] if edl.get("music") else None
    audio_in = f"{len(files)}:a" if music else ("0:a" if infos[0]["audio"] else None)
    if snap:
        if not audio_in:
            sys.exit("--snap needs an audio track")
        clips = snap_to_beats(clips, beat_times(music or files[0]))

    w = opts.get("width") or infos[0]["width"]
    h = opts.get("height") or infos[0]["height"]
    fps = opts.get("fps") or infos[0]["fps"]
    graph, vout, length = build_filter(clips, w, h, fps, opts.get("fade_in", 0))
    finish = finish_chain(opts, w, h)
    if finish:
        graph += f";[{vout}]{finish}[final]"
        vout = "final"

    starts, _ = timeline(clips)
    for c, s in zip(clips, starts):
        print(f"{s:6.2f}s  {c['shot']:<10} {c['dur']:4.2f}s  {c.get('note', '')}")
    print(f"total {length:.2f}s")

    cmd = [FFMPEG, "-y", "-hide_banner", "-v", "error"]
    for f in files + ([music] if music else []):
        cmd += ["-i", str(f)]
    maps = ["-map", f"[{vout}]"]
    if audio_in:
        afade = opts.get("audio_fade_out", 0)
        achain = f"[{audio_in}]apad,atrim=0:{length:.3f}"
        if afade:
            achain += f",afade=t=out:st={length - afade:.3f}:d={afade}"
        graph += f";{achain}[aout]"
        maps += ["-map", "[aout]", "-c:a", "aac", "-b:a", "256k"]
    cmd += ["-filter_complex", graph, *maps, "-c:v", "libx264", "-crf", "17",
            "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-t", f"{length:.3f}", str(dst)]
    subprocess.run(cmd, check=True)
    print(f"wrote {dst}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect", help="list the cut points in a video")
    d.add_argument("input")
    d.add_argument("--threshold", type=float, default=0.3)
    r = sub.add_parser("render", help="render the edit described in edl.json")
    r.add_argument("input")
    r.add_argument("output")
    r.add_argument("--edl", default=HERE / "edl.json")
    r.add_argument("--snap", action="store_true", help="snap cuts to the detected beat")
    a = ap.parse_args()
    if a.cmd == "detect":
        detect(a.input, a.threshold)
    else:
        render(a.input, a.output, a.edl, a.snap)


if __name__ == "__main__":
    main()
