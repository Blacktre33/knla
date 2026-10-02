#!/usr/bin/env python3
"""Render the animated end card: wordmark tracks in, orange rule draws, tagline fades up.

  python edit/title.py out.mp4 --font-dir path/to/montserrat [--word MosaicHaus]

Matches the original ANTIDOTE card: 1080x1920, near-black ground, cream Montserrat Bold
wordmark (cap height ~104 px) centred at y~886, 81 px orange rule at y 995, grey tracked
tagline at y~1063. Fonts: `npm pack @fontsource/montserrat` and point --font-dir at
package/files.
"""
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from recut import FFMPEG  # noqa: E402

W, H, FPS = 1080, 1920, 24
BG, CREAM, ORANGE, GREY = (8, 10, 10), (240, 234, 223), (215, 128, 54), (128, 130, 127)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def tracked(draw, text, font, cx, top, spacing, fill):
    """Draw text centred on cx with extra letter spacing; top is the cap top."""
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = cx - total / 2
    ascent_off = font.getbbox("H")[1]
    for ch, w in zip(text, widths):
        draw.text((x, top - ascent_off), ch, font=font, fill=fill)
        x += w + spacing


def fit_size(path, text, max_w, cap_h=104):
    size = 140
    while size > 40:
        f = ImageFont.truetype(path, size)
        b = f.getbbox("H")
        if b[3] - b[1] <= cap_h and f.getlength(text) + 4 * (len(text) - 1) <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(path, size)


ALPHA = False


def mix(c, a):
    if ALPHA:
        return (*c, int(255 * a))
    return tuple(int(BG[i] + (c[i] - BG[i]) * a) for i in range(3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--font-dir", required=True)
    ap.add_argument("--word", default="MosaicHaus")
    ap.add_argument("--tagline", default="STILL FEELING EVERYTHING")
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--alpha", action="store_true",
                    help="transparent background, ProRes 4444 .mov (for Final Cut / compositing)")
    a = ap.parse_args()

    global ALPHA
    ALPHA = a.alpha
    fd = Path(a.font_dir)
    word_font = fit_size(str(fd / "montserrat-latin-700-normal.woff"), a.word, 860)
    tag_font = ImageFont.truetype(str(fd / "montserrat-latin-500-normal.woff"), 22)

    mode, codec = ("RGBA", ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]) \
        if a.alpha else ("RGB", ["-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p"])
    enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo",
                            "-pix_fmt", "rgba" if a.alpha else "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", *codec, a.output], stdin=subprocess.PIPE)
    for n in range(a.frames):
        im = Image.new(mode, (W, H), (0, 0, 0, 0) if a.alpha else BG)
        d = ImageDraw.Draw(im)
        t_word = ease(n / 14)                       # wordmark: fade + track in over ~0.6 s
        tracked(d, a.word, word_font, W / 2, 834, 4 + 16 * (1 - t_word), mix(CREAM, t_word))
        rule = ease((n - 6) / 12)                   # rule draws out from the centre
        if rule > 0:
            half = 40.5 * rule
            d.rectangle([W / 2 - half, 995, W / 2 + half, 997], fill=ORANGE)
        t_tag = ease((n - 12) / 12)                 # tagline fades up last
        if t_tag > 0:
            tracked(d, a.tagline, tag_font, W / 2, 1063, 7, mix(GREY, t_tag))
        enc.stdin.write(im.tobytes())
    enc.stdin.close()
    enc.wait()
    print(f"wrote {a.output} ({a.frames} frames, wordmark {word_font.size}px)")


if __name__ == "__main__":
    main()
