---
name: video-ocr-onscreen-text
category: media
description: >
  Read text that is baked into a video's pixels — rip hardcoded/burned-in
  subtitles to a timed SRT, and log every lower-third, name super, chyron,
  scoreboard, price tag or slate caption with in/out timecodes to CSV. Uses
  videocr-PaddleOCR for subtitle rips and an ffmpeg→OCR harness (Apple Vision
  or PaddleOCR) that samples frames, OCRs each, dedupes consecutive text and
  emits timecodes. Use when someone says "extract the burned-in subtitles",
  "get the hardcoded captions to SRT", "OCR the text in this video", "log every
  name super / lower-third", "read the on-screen text with timestamps", or
  "there are no subtitle files, the captions are part of the picture".
when_to_use:
  - "A video has captions burned into the picture (no .srt/.vtt) and you need a real subtitle file"
  - "Log every lower-third / name super / title card with the timecode it appears and disappears"
  - "Pull on-screen text (scoreboard, ticker, price, product name) into a searchable CSV timeline"
  - "Transcribe foreign hardcoded subs, then translate the resulting SRT"
  - "Verify graphics/legal supers actually aired at the right moments in a finished cut"
when_not_to_use:
  - "You want the spoken dialogue transcribed, not on-screen pixels → use whisper-caption-burn (STT) or youtube-transcript-lift"
  - "The video already has a caption track / sidecar file → just extract it with ffmpeg-cookbook"
  - "You only need raw stills to eyeball, no text extraction → use video-frame-extraction"
  - "You need AI shot/scene boundaries, not text → use shot-scene-detection"
  - "You want to burn NEW captions onto a video → use whisper-caption-burn"
keywords: [ocr, burned-in subtitles, hardcoded subs, open captions, on-screen text, lower third, name super, chyron, videocr, paddleocr, apple vision, ocrmac, srt, timecode, scoreboard, ticker, image to text, screen text]
similar_to: [whisper-caption-burn, video-frame-extraction, youtube-transcript-lift, shot-scene-detection, contact-sheet-storyboard]
inputs_needed:
  - "Path to the video file"
  - "What to read: burned-in subtitle band (bottom third) vs. lower-thirds/other supers vs. whole frame"
  - "Language of the on-screen text (English → Apple Vision is easiest here; other langs → PaddleOCR lang code)"
  - "Optional time range to limit the pass, and how tight the sampling should be (subs need ~2–4 fps; supers 1 fps is fine)"
produces: A timed SRT of burned-in subtitles and/or a CSV of on-screen text blocks with in/out timecodes.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Video OCR — On-Screen Text

Read text that lives in the pixels (not in a caption track): burned-in
subtitles → SRT, and lower-thirds / supers / tickers → timecoded CSV.

## When to use

- The captions are part of the picture and there is no sidecar subtitle file.
- You need a log of every name super / lower-third with when it appears and clears.
- You want on-screen text (scores, prices, product names) as a searchable timeline.

## Prerequisites (this Mac)

**ffmpeg** — portable binary from the pip `imageio-ffmpeg` wheel (no brew here):

```bash
FF=$(python3 -c "import imageio_ffmpeg,sys; sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -version | head -1        # cache $FF; also at _research_bank/bin
```

**OCR engine** — pick one:

- **Apple Vision (recommended for English/Latin on this Mac):** native, fast,
  CPU-only, no model downloads. `python3 -m pip install --user ocrmac`
- **PaddleOCR (many languages, and the turnkey subtitle ripper):** heavier.
  `python3 -m pip install --user "git+https://github.com/devmaxxing/videocr-PaddleOCR.git"`
  This pulls `paddleocr` + `paddlepaddle`. Python 3.8–3.12 (the system 3.9 is fine).
  CPU works but is slow; there is no CUDA GPU on this Mac, so keep `use_gpu=False`
  and limit the time range / crop tightly.

Helper script (OCR a frame folder → deduped timecoded CSV/SRT):
`scripts/frames_to_ocr_log.py`.

## Recipes

### 1. Burned-in subtitles → SRT (turnkey, videocr-PaddleOCR)

Best when text sits in a stable band (usually the bottom third). videocr handles
sampling, dedupe and SRT timing for you. Crop to the subtitle band so it ignores
everything else — faster and far more accurate.

```python
from videocr import save_subtitles_to_file

save_subtitles_to_file(
    'input.mp4', 'subs.srt',
    lang='en',                 # 'ch','japan','korean','fr','german',… (PaddleOCR codes)
    time_start='0:00', time_end='',   # 'm:ss' — limit the pass while dialling in
    conf_threshold=75,         # drop low-confidence words (0–100)
    sim_threshold=80,          # merge near-identical consecutive lines (0–100)
    use_fullframe=False,       # False = bottom third only (default subtitle band)
    use_gpu=False,             # no CUDA on this Mac
    frames_to_skip=1,          # >1 = sample fewer frames = faster, coarser timing
    # crop_x=0, crop_y=620, crop_width=1280, crop_height=100,  # exact band in px
)
```

Dial-in loop: run on a 20–30s `time_start`/`time_end` window first; if lines are
missed raise `conf_threshold` down (e.g. 65) or set an explicit `crop_*` band; if
one caption splits into duplicates, raise `sim_threshold`. `get_subtitles(...)`
returns the SRT as a string instead of writing a file.

Find the band pixel coordinates by grabbing one still and inspecting it:

```bash
"$FF" -ss 00:00:30 -i input.mp4 -frames:v 1 probe.png   # open, read caption y/height
```

### 2. Lower-thirds / supers / any on-screen text → timecoded CSV (ffmpeg → OCR harness)

For text that isn't a tidy subtitle band (name supers, chyrons, tickers, slates),
sample frames yourself, crop to the region, and run the helper. It OCRs each
frame, collapses runs of the same text into one span, and writes in/out timecodes.

```bash
FF=$(python3 -c "import imageio_ffmpeg,sys; sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())")
mkdir -p frames

# Sample 1 frame/sec, cropped to a lower-third band (w:h:x:y — adjust to your frame).
# Upscale + grayscale + contrast helps OCR on thin broadcast fonts.
"$FF" -i input.mp4 -vf "fps=1,crop=1280:180:0:520,scale=iw*2:ih*2,format=gray,eq=contrast=1.4" \
      frames/f_%06d.png

# OCR every frame, dedupe, emit timecodes. --fps MUST match the fps= above.
python3 scripts/frames_to_ocr_log.py frames --fps 1 --backend vision --out lower_thirds
```

Outputs `lower_thirds.csv` (`start,end,text`) and `lower_thirds.srt`. For
non-Latin text use `--backend paddle --lang ch` (etc.). For fast-changing subtitle
text raise the rate: `fps=3` in ffmpeg **and** `--fps 3` in the helper (they must agree).

Whole-frame OCR (scattered text, no single band): drop the `crop=` term.

### 3. Foreign hardcoded subs → translate

Rip with recipe 1 (`lang='japan'`, etc.) to get a timed SRT, then translate the
text lines while keeping the timecodes — the SRT block structure is preserved so
any line-wise translation step drops straight back in.

## Verify

```bash
head -12 subs.srt                          # well-formed: index / HH:MM:SS,mmm --> ... / text
grep -c ' --> ' subs.srt                   # cue count is sane (not 0, not one-per-frame)
column -s, -t lower_thirds.csv | head      # supers read correctly with in/out timecodes
# Spot-check against the picture: pull the still at a cue's start time and read it.
"$FF" -ss 00:01:12 -i input.mp4 -frames:v 1 check.png
```

Sanity: cue count should roughly match how many distinct captions/supers you saw.
Thousands of one-word cues = sampling too fine or `sim_threshold` too low.

## Pitfalls

- **This is not speech-to-text.** OCR reads pixels. If you want spoken dialogue,
  use whisper-caption-burn — the two often disagree (supers ≠ what's said).
- **Crop first.** OCRing the full frame is slow and picks up background text/logos.
  A tight `crop` to the caption/super band is the single biggest accuracy win.
- **fps must agree.** In recipe 2 the ffmpeg `fps=` and the helper `--fps` set the
  timecodes; a mismatch shifts every timestamp. Subtitles that flash need ≥2–3 fps
  or short cues get skipped between samples.
- **Low contrast / anti-aliased fonts.** Thin white supers over busy footage OCR
  badly — add `scale=iw*2:ih*2,format=gray,eq=contrast=1.4` (as above) and, in
  videocr, tune `brightness_threshold` to knock out dark background pixels.
- **PaddleOCR install is heavy and CPU-slow here.** No GPU on this Mac; keep passes
  short (`time_start`/`time_end`), crop tight, or use `--backend vision` for
  English where Apple Vision is both native and much faster.
- **Dedupe tuning.** The helper merges spans at ~70% token overlap; genuinely
  different back-to-back supers with shared words (two people "… , Director") may
  merge — bump the sampling or eyeball the CSV. videocr's own merge is `sim_threshold`.
- **`m:ss` time format.** videocr `time_start`/`time_end` are minutes:seconds
  strings (`'7:34'`), not `HH:MM:SS`.
