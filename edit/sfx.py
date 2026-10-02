#!/usr/bin/env python3
"""Mix synthesized sound-design accents under the ANTIDOTE song.

  python edit/sfx.py Music_00-30.wav Music_sfx.wav          # song + accents
  python edit/sfx.py Music_00-30.wav SFX_stem.wav --stem     # accents only (for an editor)

Accents are placed in frames at 24 fps, matching edl_v4.json:
riser into the bass drop, sub boom + water plip on the drop, swell into the
petal lift, low hit under the title card.
"""
import subprocess
import sys

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__file__))
from recut import FFMPEG  # noqa: E402

SR, FPS = 48000, 24
rng = np.random.default_rng(7)


def sec(frames):
    return frames / FPS


def lowpass_sweep(x, f0, f1):
    """One-pole lowpass whose cutoff glides exponentially from f0 to f1."""
    fc = f0 * (f1 / f0) ** np.linspace(0, 1, len(x))
    a = np.exp(-2 * np.pi * fc / SR)
    y, prev = np.empty_like(x), 0.0
    for i, (xi, ai) in enumerate(zip(x, a)):
        prev = (1 - ai) * xi + ai * prev
        y[i] = prev
    return y


def riser(dur, f0=250, f1=9000):
    n = int(dur * SR)
    env = np.linspace(0, 1, n) ** 3
    return lowpass_sweep(rng.standard_normal(n), f0, f1) * env * 3


def boom(dur=1.4, f0=58, f1=30):
    t = np.arange(int(dur * SR)) / SR
    phase = 2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t / dur)) / SR
    click = rng.standard_normal(len(t)) * np.exp(-t * 90) * 0.4
    return (np.sin(phase) * np.exp(-t * 2.6) + click) * np.minimum(1, t * 400)


def plip(dur=0.12):
    t = np.arange(int(dur * SR)) / SR
    f = 900 + 2600 * t / dur
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45)


def place(track, clip, start, gain_db):
    i = int(start * SR)
    seg = clip[: len(track) - i] * 10 ** (gain_db / 20)
    track[i:i + len(seg)] += seg


def main(src, dst, stem_only=False):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", src, "-ac", "2", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    song = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    fx = np.zeros(len(song))

    place(fx, riser(sec(133 - 89)), sec(89), -24)        # drop falls -> tension
    place(fx, boom(), sec(133), -10)                     # bass drop: impact
    place(fx, plip(), sec(133), -20)                     # the drop hits water
    place(fx, riser(sec(397 - 375), 600, 12000), sec(375), -28)  # into the petal lift
    place(fx, boom(1.8, 50, 28), sec(661), -12)          # title card

    out = (fx[:, None] * np.ones((1, 2))) if stem_only else song + fx[:, None]
    peak = np.abs(out).max()
    if peak > 0.98:
        out *= 0.98 / peak
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2",
                    "-i", "-", "-c:a", "pcm_s24le", dst], input=out.astype(np.float32).tobytes(),
                   check=True)
    print(f"wrote {dst} (peak {20 * np.log10(peak):.1f} dBFS before limiting)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--stem" in sys.argv[3:])
