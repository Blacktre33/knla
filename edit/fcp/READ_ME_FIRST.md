# MosaicHaus v6: Final Cut Pro project

30 s · 1080×1920 (9:16) · 24 fps · Rec. 709 · stereo 48 kHz

```
MosaicHaus_FCP_v6/
  MosaicHaus_v6.fcpxml   the editable timeline (FCPXML 1.10)
  Media/                 all clips, ProRes; title + flash are ProRes 4444 with alpha
  LUTs/                  grade: MosaicHaus_look.cube + one colour-match LUT per generated shot
  Preview_graded.mp4     what the finished grade should look like (reference only)
```

## 1. Import

0. **Add the original clips.** This package carries only the new media. From ChatGPT's
   `ANTIDOTE_Final_Cut_v2/Media` folder, copy `01_…` to `11_…` (.mov) and `Music_00-30.wav` into
   this package's `Media/` folder.
1. Keep `Media/` next to the `.fcpxml`.
2. Final Cut Pro → **File → Import → XML…** → `MosaicHaus_v6.fcpxml`.
3. A new event "MosaicHaus v6" appears with the project inside.
4. If clips show as missing (red), select the event → **File → Relink Files…** → **Locate All** →
   choose the `Media` folder.

## 2. What's on the timeline (all editable)

* **Primary storyline:** 21 shots cut on the beat (the song is 130.9 BPM = 11 frames per beat).
* **Markers** on the five musical hits: bass drop 5.54 s, hi-hats 7.38 s, petal lift 16.54 s,
  breakdown 22.04 s, title 27.54 s.
* **Retimes:** the falling drop, the slow-motion runway walk and the petal lift
  (optical flow). Change them in the Retime menu.
* **Push-ins / punch-ins:** Transform → Scale keyframes on the hits (Video inspector).
* **Fade-up:** Opacity keyframes on the first shot.
* **White flash:** a 3-frame connected clip above the puddle impact; delete it or change its opacity.
* **Audio:** the song (role *Music*) and the sound-design stem (role *Effects*: riser, boom,
  water plip, swell, title hit) on separate lanes. Balance them independently.
* **Title:** `15_Title_MosaicHaus.mov`, an animated clip with transparency. You can drag it onto a
  connected lane over footage too.

## 3. Grade: apply the LUTs (about 2 minutes)

Final Cut's **Custom LUT** effect (Effects browser → Color → Custom LUT) keeps each grade as an
editable, removable effect.

1. **Match the generated shots first.** On each of these clips add Custom LUT and choose its file:
   * `hanky_cu` (16_Hanky_closeup) → `16_Hanky_closeup_match.cube`
   * `hero` (17_Hero_walk_low) → `17_Hero_walk_low_match.cube`
   * `petals` (13_Petals_lift_macro) → `13_Petals_lift_macro_match.cube`
   * `looks_up` (14_Lead_looks_up) → `14_Lead_looks_up_match.cube`
2. **Then the look on every shot except the title.** Add a second Custom LUT →
   `MosaicHaus_look.cube` to one clip, **Copy** it, select the other clips, then
   **Edit → Paste Effects**. The look LUT must sit *below* the match LUT in the inspector.
3. Optional finish:
   * film grain: a grain overlay, or Final Cut's built-in noise/film effects at a low amount
   * a light **Vignette**
   * a few frames of Position keyframes on the impact (5.54 s) for a camera shake

Compare against `Preview_graded.mp4`.

## 4. Export

**File → Share → Master File** → Apple ProRes 422 HQ for the master, and H.264 at
1080×1920 for Reels/TikTok/Shorts.

## Notes

* Generated in a cloud workspace. The FCPXML was checked structurally (no gaps, every clip within
  its media, 720 frames), but **not test-imported into Final Cut on a Mac**. If the import
  reports an error, send the message back and it can be fixed.
* Shots 13, 14, 16 and 17 were generated with Higgsfield (Kling 3.0); the title was rendered
  with Montserrat Bold.
