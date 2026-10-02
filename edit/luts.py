#!/usr/bin/env python3
"""Build .cube LUTs for Final Cut Pro's Custom LUT effect (or Resolve/Premiere).

  python edit/luts.py MEDIA_DIR OUT_DIR

* <clip>_match.cube: per generated clip, moves its colour statistics (mean/spread in Lab)
  onto the original ANTIDOTE footage, so the Higgsfield shots sit in the same grade.
* MosaicHaus_look.cube: the overall film look, applied after the match: slightly lifted
  blacks, gentle S-curve, warm saffron highlights, cooler mint shadows, a touch less
  saturation outside the oranges.

Each LUT is a 33-point Rec.709 cube, so every grade stays an editable, removable effect.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from recut import FFMPEG  # noqa: E402

N = 33
REFERENCE = ["01_Opening_portrait", "02_Lead_and_tear", "04_Runway_entrance",
             "09_Rising_marigolds", "10_Shoulder_comfort", "11_Return_portrait"]
GENERATED = ["13_Petals_lift_macro", "14_Lead_looks_up", "16_Hanky_closeup", "17_Hero_walk_low"]


def frames(path, count=6, w=270, h=480):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-vf",
                          f"thumbnail=12,scale={w}:{h}", "-frames:v", str(count), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.float64) / 255


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.95047, 1.0, 1.08883])


def rgb_to_lab(rgb):
    xyz = srgb_to_lin(rgb) @ M.T / WHITE
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def lab_to_rgb(lab):
    fy = (lab[:, 0] + 16) / 116
    f = np.stack([fy + lab[:, 1] / 500, fy, fy - lab[:, 2] / 200], 1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * WHITE
    return lin_to_srgb(xyz @ np.linalg.inv(M).T)


def grid():
    r = np.linspace(0, 1, N)
    b, g, rr = np.meshgrid(r, r, r, indexing="ij")      # .cube order: red fastest
    return np.stack([rr.ravel(), g.ravel(), b.ravel()], 1)


def write_cube(path, title, rgb):
    with open(path, "w") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {N}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        for p in np.clip(rgb, 0, 1):
            f.write(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")


def match_lut(src_lab, ref_lab, strength=(0.5, 0.8, 0.8)):
    """Reinhard-style statistics transfer in Lab, softened so it never over-corrects.

    Lightness moves only halfway: a dark macro shot should stay darker than a wide."""
    ms, ss = src_lab.mean(0), src_lab.std(0) + 1e-6
    mr, sr = ref_lab.mean(0), ref_lab.std(0)
    lab = rgb_to_lab(grid())
    moved = (lab - ms) * (sr / ss) + mr
    return lab_to_rgb(lab + np.array(strength) * (moved - lab))


def look_lut():
    rgb = grid()
    x = 0.03 + 0.94 * rgb                                   # lift blacks, roll highlights
    x = x + 0.12 * (x - 0.5) * (1 - np.abs(2 * x - 1))      # gentle S-curve
    luma = x @ np.array([0.2126, 0.7152, 0.0722])
    lab = rgb_to_lab(np.clip(x, 0, 1))
    hue = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
    orange = np.exp(-((hue - 60) / 28) ** 2)                # saffron / marigold band
    lab[:, 1:] *= (0.88 + 0.16 * orange)[:, None]           # keep oranges, calm the rest
    x = lab_to_rgb(lab)
    shadows, highs = np.clip(1 - 2 * luma, 0, 1), np.clip(2 * luma - 1, 0, 1)
    x += shadows[:, None] * np.array([-0.012, 0.006, 0.010])    # mint shadows
    x += highs[:, None] * np.array([0.018, 0.006, -0.016])      # warm highlights
    return x


def main(media, out):
    media, out = Path(media), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ref = rgb_to_lab(np.concatenate([frames(media / f"{n}.mov") for n in REFERENCE]))
    for name in GENERATED:
        src = rgb_to_lab(frames(media / f"{name}.mov"))
        write_cube(out / f"{name}_match.cube", f"{name} to ANTIDOTE", match_lut(src, ref))
        print(f"{name}: L {src[:, 0].mean():.1f}->{ref[:, 0].mean():.1f}  "
              f"a {src[:, 1].mean():.1f}->{ref[:, 1].mean():.1f}  b {src[:, 2].mean():.1f}->{ref[:, 2].mean():.1f}")
    write_cube(out / "MosaicHaus_look.cube", "MosaicHaus look", look_lut())
    print(f"wrote LUTs to {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
