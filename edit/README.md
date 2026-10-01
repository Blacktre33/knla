# ANTIDOTE: re-cut

A new edit of the 30 s *ANTIDOTE — Still Feeling Everything* film. It is built only from footage
already in the current export, and the music runs underneath untouched.

## What was wrong with the current cut

Scene analysis of the export found 17 cuts made from only 11 different shots:

| time | shot | problem |
|---|---|---|
| 0:00–0:14 | puddle → shoes → elder → group → walk → **shoes again** → nose-wipe → **walk again** → two-shot → face → **puddle again** | cuts every ~1 s with no direction. Repeated shots come back before the viewer has missed them, so it feels like a loop |
| 0:14–0:21 | marigold wide, 7 s | the one big moment lands in the middle and stops the momentum dead after 14 s of fast cutting |
| 0:21–0:26 | elder → **face again** → **marigolds again** | the ending repeats the middle, so there's no build |
| 0:26–0:27 | **puddle again** | that's the 3rd puddle, so the bookend doesn't feel special |
| 0:27 | hard cut to black card, music stops | abrupt. The card arrives with no breath |

Underneath that, the film already has a story that the edit hides. The friend wipes his nose with
a pink cloth, rests his head on the elder's shoulder, a drop sits on the elder's moustache, and the
tagline is *still feeling everything*. **It's about men crying in public.** The new edit is built
around that.

## The new structure

| new time | shot | why |
|---|---|---|
| 0:00 | puddle ripple (fade up from black, slowed slightly) | cold open, mood |
| 0:01.25 | shoes in the puddle | match cut: the reflection becomes the shoes |
| 0:02.25 | walk → shoes → walk | **arrival**: feet and stride cut on the beat, match on action |
| 0:05.25 | group wide | the crew is revealed once they've arrived |
| 0:07.25 | elder seated, friend wiping nose behind him | plants the emotion |
| 0:09.25 | CU nose-wipe | **the feeling** |
| 0:10.25 | head on shoulder, eyes to camera | comfort |
| 0:12.25 | ECU: drop on the moustache | the tear |
| 0:13.25 | puddle ripple | match cut: the tear lands in the puddle |
| 0:13.75 | **soft dissolve** → marigolds, slow-mo | **release**: the payoff, now earned |
| 0:20.75 | ECU face → marigolds closer → elder's final stare | quiet coda, each shot used once |
| 0:25.75 | puddle ripple | bookend, used for the last time |
| 0:26.5 | **fade through black** → ANTIDOTE card | the card lands as the music resolves |

Transitions are used on purpose: hard cuts for the rhythm, and just two soft ones at the two
emotional turns (into the flowers, and into the card). No zooms or whips. They'd fight the
lo-fi mood.

## Run it

```bash
pip install imageio-ffmpeg numpy      # or have ffmpeg on PATH
python edit/recut.py detect antidote.mp4             # check the real cut points
python edit/recut.py render antidote.mp4 recut.mp4   # render
python edit/recut.py render antidote.mp4 recut.mp4 --snap   # also lock cuts to the beat
```

* **Check the in/out points first.** The source times in `edl.json` come from scene analysis
  rounded to whole seconds. `detect` prints the exact cut points of the export. If a clip in the
  render flashes a frame of the neighbouring shot, nudge its `in`/`out` by ~0.05 s.
* **`--snap`** estimates the tempo of the music and moves every cut to the nearest beat (within
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
