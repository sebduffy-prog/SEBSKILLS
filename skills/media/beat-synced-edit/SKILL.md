---
name: beat-synced-edit
category: media
description: >
  Cut video to the beat of music — detect the beat grid, downbeats, or transient
  onsets in a track with librosa (beat_track / onset_detect), then hard-cut a
  montage so every clip change lands on a beat. Produces a beat-times list AND a
  rendered beat-synced montage (one clip per beat interval) via ffmpeg. Use when
  someone says "cut this to the beat", "beat-synced edit", "music video montage",
  "sync clips to the music", "cut on the drop", "hype reel to a track", "make it
  hit on the beat", or "flash cuts on the downbeat" for a social or brand reel.
when_to_use:
  - Build a montage/hype reel where every cut lands on a musical beat or downbeat
  - Extract beat/onset timestamps from a song to drive an edit or animation
  - Cut on downbeats only (every 2nd/4th beat) for a slower, punchier feel
  - Sync flash-cuts, zooms, or graphic hits to the drop in a social/brand video
  - Turn a folder of raw clips + a track into a rendered beat-cut video
when_not_to_use:
  - Cutting on speech pauses / dead air, not music → use auto-silence-cut
  - Cutting on scene or shot changes in existing footage → use shot-scene-detection
  - Plain trim / concat / re-encode with no beat analysis → use ffmpeg-cookbook
  - Reframing aspect ratio 16:9 → 9:16 → use social-video-reframe
  - Slicing one long video into topic shorts → use long-video-to-shorts
keywords: [beat sync, beat detection, librosa, beat_track, onset detection, music video, montage, downbeat, bpm, ffmpeg, cut to the beat, hype reel, tempo, transient, flash cut, rhythm edit, onset_detect]
similar_to: [auto-silence-cut, shot-scene-detection, ffmpeg-cookbook, social-video-reframe, long-video-to-shorts]
inputs_needed:
  - A music track (audio or the audio of a video) to detect beats in
  - Source clips (a folder, file list, or globs) to assemble — for the montage step
  - Feel intent — cut on every beat, half-time, or downbeats (--every); vertical vs landscape
produces: A beat-times list (stdout/JSON) and/or a rendered beat-synced montage MP4 with the music laid over
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Beat-Synced Edit

Detect the rhythm of a track, then cut video so every clip change hits on a beat.
Two stages, each a small helper: **detect** beat times, then **assemble** a montage.

## When to use

Reach for this when the edit's rhythm must come from the music — brand hype reels,
social montages, "cut on the drop" openers. If you only need the timestamps (to
drive After Effects keyframes, a web animation, or a hand edit), stop after stage 1.

## Prerequisites

- **Python 3.9+** with `librosa` (`pip install --user librosa soundfile`). Verified
  against **librosa 0.11** — `librosa.beat.beat_track` and `librosa.onset.onset_detect`.
- **ffmpeg** — system `ffmpeg`, or the bundled `imageio_ffmpeg` binary. Both scripts
  auto-fall-back to `imageio_ffmpeg.get_ffmpeg_exe()` when `ffmpeg` is not on PATH
  (this Mac has no system ffmpeg — install with `pip install --user imageio-ffmpeg`).
- Beat tracking is **estimation**: it locks well to steady 4/4 dance/pop, drifts on
  rubato, ambient, or heavily syncopated music. Always sanity-check the times.

## Recipes

### 1. Detect beat times

```bash
S=skills/media/beat-synced-edit/scripts
# Beat grid (prints tempo to stderr, one time per line to stdout)
python3 $S/beat_times.py song.mp3
# JSON with tempo, straight into a pipeline
python3 $S/beat_times.py song.mp3 --json
# Works on a video too — audio is extracted with ffmpeg first
python3 $S/beat_times.py reel_source.mp4 --json
```

Save the grid for the assembly step:

```bash
python3 $S/beat_times.py song.mp3 > times.txt
```

**Tuning knobs:**

- `--every N` — keep every Nth beat. `--every 2` = half-time (~2 cuts/bar in 4/4),
  `--every 4` ≈ downbeats (one cut per bar). This is the main "make it breathe" dial.
- `--offset SEC` — shift every time to line the grid up with the true downbeat
  (nudge until cut 1 lands where the bar starts).
- `--start-bpm 140 --tightness 100` — hint the tempo when librosa octave-halves
  (reports ~70 for a 140 track) or locks onto the wrong pulse. Raise `--tightness`
  for a stricter, more regular grid.
- `--onsets` — ignore the metrical grid and cut on **transients** (every kick, snare,
  vocal stab). Denser and less regular — good for glitchy, percussive edits.

### 2. Assemble a beat-synced montage

`beat_montage.py` takes one clip per beat interval, trims each to the exact gap
between two beats, scales/crops to frame, concatenates, and lays the music on top.

```bash
python3 $S/beat_montage.py \
  --clips ./raw_clips \                # folder, file list, or globs
  --times times.txt \
  --music song.mp3 \
  --out montage.mp4 \
  --size 1080x1920 \                   # vertical 9:16 (default); use 1920x1080 for landscape
  --fps 30 \
  --start-at 0.5 \                     # skip the first 0.5s of each clip
  --max-clips 24                       # cap the number of cuts
```

Clips are used in sorted order, cycling if there are fewer clips than intervals.
Clips shorter than an interval are looped-then-trimmed to fill it, so short b-roll
still works. Output carries `--music` for its full montage length.

### 3. Downbeat-only edit (slower, punchier)

```bash
python3 $S/beat_times.py song.mp3 --every 4 --offset 0.25 > downbeats.txt
python3 $S/beat_montage.py --clips ./raw_clips --times downbeats.txt \
  --music song.mp3 --out downbeat_cut.mp4 --size 1080x1920
```

### 4. Times only, for another tool (AE / web / NLE)

`--json` emits `{"tempo": ..., "times": [...]}`. Feed `times` into After Effects
keyframes, a `requestAnimationFrame` timeline, or a marker track. No render needed.

## Verify

- Tempo printed to stderr should match the track (tap-along, or check the artist's
  known BPM). If it reads ~half or ~double, re-run with `--start-bpm`.
- Overlay the grid on the waveform: the times should sit on the kick/snare hits.
- Play the montage: cuts must land *on* the beat, not a frame late. If consistently
  early/late, nudge `--offset` (a few hundredths of a second).
- Smoke test end-to-end (synthetic click track + test clips):
  ```bash
  python3 -c "import librosa,imageio_ffmpeg; print('ok', librosa.__version__)"
  python3 $S/beat_times.py song.mp3 --json   # prints tempo + times
  ```

## Pitfalls

- **Octave errors.** librosa often reports half/double the real tempo on sparse or
  bass-heavy tracks. Fix with `--start-bpm` near the true value.
- **Grid vs downbeat.** `beat_track` finds the *beat pulse*, not bar starts. Use
  `--offset` to align cut 1 to the downbeat; `--every 4` to cut once per bar.
- **Non-steady music.** Rubato, live tempo drift, ambient, and free-time sections
  defeat beat tracking — fall back to `--onsets` or place cuts by hand.
- **Too-short clips look frozen.** With `--every 1` on a 140 BPM track each cut is
  ~0.43s; looping a 0.2s clip reads as a stutter. Give clips ≥ the interval, or
  slow the grid with `--every 2`/`--every 4`.
- **Audio drift on concat.** The montage re-encodes each segment to a uniform fps
  before concat (avoids the "-c copy" timestamp glitches). Keep `--fps` consistent
  with your delivery spec.
- **First/last beat.** `beat_track` may miss the very first onset or add a trailing
  beat; trim `times.txt` by hand for a clean top and tail.
