# ANTIDOTE: re-cut

A new edit of the 30 s *ANTIDOTE — Still Feeling Everything* film. It is built only from footage
already in the current export, and the music runs underneath untouched.

## What was wrong with the current cut

Measured on the actual export (1080x1920, 24 fps, 30 s):

* **The music has a shape the edit ignores.** It's a quiet intro until the beat drops at exactly
  **5.50 s**, then full energy until **21.5 s**, then a softer outro that fades at 29.5 s. The
  music is 130.9 BPM, which is exactly **11 frames per beat**.
* **Cuts are a frame late.** Most cuts land 1 frame (42 ms) after the beat (3.71, 4.62,
  5.54, 6.46 …), so the cutting feels slightly sluggish.
* **There's a stray 0.25 s black flash at 7.2 s** and a 1-frame shot at 7.38 s, both off the beat.
* **The same footage is reused too often.** The same face close-up appears 5 times, the puddle
  4 times and the walk 3 times. Shots come back before you miss them, so it plays like a loop.
* **The story is buried.** The friend wipes his nose with a pink cloth, rests his head on the
  elder's shoulder, a tear runs down the elder's cheek, and the tagline is *still feeling
  everything*. It's about men crying in public.

## The new structure

Every cut sits on the 11-frame beat grid.

| time | shots | music |
|---|---|---|
| 0:00 | puddle (fade up) → shoes → torso, face withheld → friend wiping his nose | quiet intro, 1–2 bars per shot |
| **0:05.50** | **the face and the tear, held a full bar** | **the drop** |
| 0:07.33 | walk → shoes / torso on single beats → crew → stack → walk → wipe | full energy, cutting on the beat |
| 0:13.75 | face → puddle (the tear lands) → **dissolve** into the marigolds, 6.4 s | release |
| 0:21.54 | head on shoulder → last look → marigolds → walk → puddle bookend | outro, the music eases |
| 0:26.58 | **fade through black** → ANTIDOTE card, held 3 s | the music resolves under the card |

There are only two soft transitions, at the two emotional turns. Everything else is a hard cut on
the beat. The face close-up now appears 3 times (at the drop, before the tear, last look) instead
of 5, and the black flash is gone.

## Run it

```bash
pip install imageio-ffmpeg numpy      # or have ffmpeg on PATH
python edit/recut.py detect antidote.mp4             # check the real cut points
python edit/recut.py render antidote.mp4 recut.mp4   # render
```

* The in/out times in `edl.json` are taken from the export's real cut points (`detect` prints
  them), and are frame-accurate.
* **`--snap`** is for other edits and isn't needed here, since this edit list is already on the grid. It estimates the tempo of the music and moves every cut to the nearest beat (within
  a third of a beat), keeping the total at 30 s. Clips stretch or squeeze slightly to fit.
* Everything is in `edl.json`: re-order clips, change `dur`, or add
  `"transition": {"type": "fade", "dur": 0.5}` to any clip. Any ffmpeg `xfade` name works
  (`fade`, `fadeblack`, `dissolve`, `smoothleft`, `circleopen`, …).
* Output keeps the source resolution and frame rate unless `output.width/height/fps` are set.

## If you have the original footage

Re-cutting a finished export works, but every shot is capped at the ~1–2 s that survived the
first edit. With the raw clips, the walk can run as one continuous take, the marigolds can start
before they fall, and the nose-wipe can play out. Add them to the repo and the same structure can
be rebuilt from the raw clips (the script would need a per-clip source file, which is a small change).
