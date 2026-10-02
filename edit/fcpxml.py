#!/usr/bin/env python3
"""Export a frame-unit edit list (edl_v6.json) as an editable Final Cut Pro FCPXML 1.10 project.

  python edit/fcpxml.py edit/edl_v6.json PACKAGE_DIR/MosaicHaus_v6.fcpxml --media PACKAGE_DIR/Media

Everything stays native and editable in Final Cut:
* each shot is its own clip on the primary storyline, cut on the 11-frame beat grid;
* speed changes are retimes (optical flow where the render used motion interpolation);
* push-ins and punch-ins are Transform > Scale keyframes;
* the white flash on the bass drop is a connected clip above the impact (delete or move it);
* the song and the sound-design stem are separate connected audio clips;
* the first clip fades up from black with Compositing > Opacity keyframes;
* markers sit on the musical hits.
Media paths are written relative to the .fcpxml (file:./Media/...); if Final Cut shows the
clips offline, use File > Relink Files.
"""
import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from xml.sax.saxutils import quoteattr

sys.path.insert(0, str(Path(__file__).parent))
from recut import FFMPEG  # noqa: E402

FPS = 24
HITS = {133: "Bass drop: impact", 177: "Hi-hats in: hero walk", 397: "Bar: petals lift",
        529: "Breakdown: comfort", 661: "Last bar: title"}


def t(frames):
    """Rational FCPXML time for a frame count at 24 fps."""
    f = Fraction(frames).limit_denominator(1000)
    if f == 0:
        return "0s"
    v = f / FPS
    return f"{v.numerator}/{v.denominator}s" if v.denominator != 1 else f"{v.numerator}s"


def frame_count(path):
    err = subprocess.run([FFMPEG, "-i", str(path), "-map", "0:v", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return int(re.findall(r"frame=\s*(\d+)", err)[-1])


def scale_keys(c, base):
    """Scale keyframes for push [z0, z1] and decaying punch [amount, frames]; times in clip time."""
    fx = c.get("fx", {})
    z0, z1 = fx.get("push", (1.0, 1.0))
    pts = {0, c["dur"]}
    if "punch" in fx:
        pts |= {fx["punch"][1], max(1, fx["punch"][1] // 2)}

    def z(n):
        v = z0 + (z1 - z0) * n / c["dur"]
        if "punch" in fx:
            amp, frames = fx["punch"]
            v *= 1 + amp * max(0.0, 1 - n / frames)
        return v

    if "push" not in fx and "punch" not in fx:
        return ""
    keys = "".join(f'<keyframe time="{t(base + n)}" value="{z(n):.4f} {z(n):.4f}"/>'
                   for n in sorted(p for p in pts if p <= c["dur"]))
    return f'<adjust-transform><param name="scale" key="scale"><keyframeAnimation>{keys}' \
           f'</keyframeAnimation></param></adjust-transform>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("output")
    ap.add_argument("--media", required=True)
    ap.add_argument("--name", default="MosaicHaus v6")
    a = ap.parse_args()

    edl = json.loads(Path(a.edl).read_text())
    media = Path(a.media)
    rel = Path(media.name)

    def local(src):
        stem = Path(edl["sources"][src]).stem
        return next(p for p in sorted(media.glob(stem + ".*")) if p.suffix in (".mov", ".mp4"))

    res, ids = [], {}
    res.append(f'<format id="r1" name="MosaicHaus 1080x1920 24p" frameDuration="1/24s" '
               f'width="1080" height="1920" colorSpace="1-1-1 (Rec. 709)"/>')

    def asset(key, path, video=True, frames=None):
        if key in ids:
            return ids[key]
        rid = f"r{len(ids) + 2}"
        ids[key] = rid
        src = f"./{rel.as_posix()}/{path.name}"
        if video:
            res.append(f'<asset id="{rid}" name={quoteattr(path.stem)} start="0s" duration="{t(frames)}" '
                       f'hasVideo="1" format="r1" videoSources="1">'
                       f'<media-rep kind="original-media" src={quoteattr(src)}/></asset>')
        else:
            res.append(f'<asset id="{rid}" name={quoteattr(path.stem)} start="0s" duration="30s" '
                       f'hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000">'
                       f'<media-rep kind="original-media" src={quoteattr(src)}/></asset>')
        return rid

    spine, offset = [], 0
    for i, c in enumerate(edl["clips"]):
        path = local(c["src"])
        rid = asset(c["src"], path, frames=frame_count(path))
        src_len = c["out"] - c["in"]
        retimed = src_len != c["dur"]
        fx = c.get("fx", {})
        base = 0 if retimed else c["in"]
        start = t(base)
        inner = ""
        if retimed:
            sampling = "optical-flow" if fx.get("smooth") else "frame-blending"
            inner += (f'<timeMap frameSampling="{sampling}">'
                      f'<timept time="0s" value="{t(c["in"])}" interp="linear"/>'
                      f'<timept time="{t(c["dur"])}" value="{t(c["out"])}" interp="linear"/></timeMap>')
        inner += scale_keys(c, base)
        if i == 0 and edl["output"].get("fade_in"):
            fade = round(edl["output"]["fade_in"] * FPS)
            inner += (f'<adjust-blend><param name="amount" key="amount"><keyframeAnimation>'
                      f'<keyframe time="{t(base)}" value="0"/><keyframe time="{t(base + fade)}" value="1"/>'
                      f'</keyframeAnimation></param></adjust-blend>')
        if i == 0:
            song = asset("music", media / "Music_00-30.wav", video=False)
            stem = asset("sfx", media / "SFX_stem.wav", video=False)
            inner += (f'<asset-clip ref="{song}" name="Antidote (sped up) 0:00-0:30" lane="-1" '
                      f'offset="{start}" start="0s" duration="30s" audioRole="music"/>'
                      f'<asset-clip ref="{stem}" name="Sound design stem" lane="-2" '
                      f'offset="{start}" start="0s" duration="30s" audioRole="effects"/>')
        if "flash" in fx:
            flash = media / "FX_White_flash.mov"
            fid = asset("flash", flash, frames=frame_count(flash))
            inner += (f'<asset-clip ref="{fid}" name="White flash" lane="1" offset="{start}" '
                      f'start="0s" duration="{t(frame_count(flash))}"/>')
        for hit, label in HITS.items():
            if offset <= hit < offset + c["dur"]:
                inner += f'<marker start="{t(base + hit - offset)}" duration="1/24s" value={quoteattr(label)}/>'
        note = f'<note>{c["note"]}</note>' if c.get("note") else ""
        spine.append(f'<asset-clip name={quoteattr(c["shot"])} ref="{rid}" offset="{t(offset)}" '
                     f'start="{start}" duration="{t(c["dur"])}" format="r1" tcFormat="NDF">'
                     f'{note}{inner}</asset-clip>')
        offset += c["dur"]

    xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10">'
           f'<resources>{"".join(res)}</resources><library><event name={quoteattr(a.name)}>'
           f'<project name={quoteattr(a.name)}><sequence format="r1" duration="{t(offset)}" '
           f'tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k"><spine>'
           f'{"".join(spine)}</spine></sequence></project></event></library></fcpxml>\n')
    Path(a.output).write_text(xml)
    print(f"wrote {a.output}: {len(spine)} clips, {offset} frames ({offset / FPS:.2f}s)")


if __name__ == "__main__":
    main()
