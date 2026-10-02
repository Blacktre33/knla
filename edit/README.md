# ANTIDOTE: re-cut

## v6 (`edl_v6.json`): MosaicHaus

* **Handkerchief close-up** (new; GPT Image 2.5 start frame + Kling 3.0) at 1.88 s: the friend
  finishes dabbing his eye and stares into the lens, then the elder's tear, then the drop.
* **Low hero walk** (new, same pipeline) on the hi-hat entry at 7.38 s: silver sneakers
  stepping through the puddle, camera on the asphalt.
* **Animated end card** (`title.py`): "MosaicHaus" in Montserrat Bold tracks in, the orange
  rule draws, then the tagline fades up. Same layout as the original card.

```bash
npm pack @fontsource/montserrat && tar xzf fontsource-montserrat-*.tgz
python edit/title.py ANTIDOTE_Final_Cut_v2/Media/15_Title_MosaicHaus.mp4 --font-dir package/files
python edit/recut.py render ANTIDOTE_Final_Cut_v2 mosaichaus_v6.mp4 --edl edit/edl_v6.json
```

New media: `Media/16_Hanky_closeup.mp4`, `Media/17_Hero_walk_low.mp4`.

## v5 (`edl_v5.json`): v4 plus new shots, sound design and finish

* **Two new Higgsfield shots (Kling 3.0, started from frames of the existing footage)** in the
  petal moment: a macro of the marigolds leaving the wet asphalt around the sneakers, right on
  the 16.54 s bar, then the wide slow motion, then the elder lifting his chin as flowers float
  past. Save them as `Media/13_Petals_lift_macro.mp4` and `Media/14_Lead_looks_up.mp4`.
* **Sound design** (`sfx.py`, mixed into `Media/Music_sfx.wav`): a riser while the drop falls, a
  sub boom and water plip on the bass drop, an airy swell into the petal lift, and a low hit under
  the title.
* **Finish:** film grain to bind the AI clips together, a light vignette, and a decaying camera
  shake on the impact and the title.

```bash
python edit/sfx.py ANTIDOTE_Final_Cut_v2/Media/Music_00-30.wav ANTIDOTE_Final_Cut_v2/Media/Music_sfx.wav
python edit/recut.py render ANTIDOTE_Final_Cut_v2 antidote_v5.mp4 --edl edit/edl_v5.json
```

## v4: the "impact" cut (`edl_v4.json`)

The brief, from the original ChatGPT conversation: a crybabycore fashion music video on
*Antidote (sped up)*, about "fast music, slow bodies, tiny cracks in composure", with one impossible
event (the marigolds **rise**). The feedback on every earlier version was that it had **no suspense
and no impact moments**. So v4 puts every visual hit exactly on a hit in the song.

Built from the original clips in ChatGPT's Final Cut package (`ANTIDOTE_Final_Cut_v2/Media`),
over the clean `Music_00-30.wav` with none of V3's baked-in audio dips. The song is 130.9 BPM,
which is 11 frames per beat at 24 fps, with beats on frame 11k+1.

| time | frame | music | picture |
|---|---|---|---|
| 0:00 | 0 | intro, no bass | portrait → tear → handkerchief, slow push-ins. They hold their composure |
| 0:04.6 | 111 | last beat before the drop | the drop **falls in slow motion**: suspense |
| **0:05.54** | **133** | **bass drop** | **the drop hits the puddle on the bass drop**, with a white flash and a punch-in |
| **0:07.38** | **177** | **hi-hats enter** | **runway entrance**, played slower than the music, with a punch-in |
| 0:11.0 | 265 | full groove | fashion percussion: sneaker / patch / walk / sneaker / sunglasses / walk, one per beat |
| 0:14.7 | 353 | | marigolds on the ground: stillness |
| **0:16.54** | **397** | **bar line** | **the petals lift off**, ramped into smooth (motion-interpolated) slow motion for 5.5 s |
| **0:22.04** | **529** | **breakdown, hats drop out** | head on shoulder: the antidote |
| 0:25.7 | 617 | outro | back to the portrait, pulling away |
| **0:27.54** | **661** | **last bar** | **hard cut to ANTIDOTE** |

```bash
# needs the unzipped Final Cut package, plus the V3 export saved inside it as antidote_v3.mp4 (for the title card)
python edit/recut.py render ANTIDOTE_Final_Cut_v2 antidote_v4.mp4 --edl edit/edl_v4.json
```

Per-clip effects live in `fx`: `push` [start, end zoom], `punch` [amount, frames], `flash`
(frames of white), and `smooth` (motion-interpolated slow motion).

---

## v3 re-cut of the export (`edl.json`)

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
