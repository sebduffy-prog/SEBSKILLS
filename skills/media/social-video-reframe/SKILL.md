---
name: social-video-reframe
category: media
description: >
  Reframe (recrop) horizontal 16:9 video into vertical 9:16, square 1:1, or portrait
  4:5 for Reels, Shorts, and TikTok — with subject-aware smart crop so heads and
  speakers are not sliced off. Produces a re-encoded MP4 at the target aspect ratio.
  Use whenever someone says "make this a reel", "turn my landscape edit vertical",
  "9:16 crop", "1:1 for the feed", "portrait crop for TikTok", "recrop and keep the
  presenter centred", or "convert 16:9 to 9:16 without cropping the face".
when_to_use:
  - Turning a 16:9 edit into a 9:16 vertical reel for TikTok / Reels / Shorts
  - Making a 1:1 square or 4:5 portrait crop for an Instagram / LinkedIn feed
  - Keeping a single speaker or subject centred in frame while reframing
  - Batch-reframing a folder of horizontal clips to one social aspect ratio
  - Needing a blurred-background "fit" version so nothing is cropped at all
when_not_to_use:
  - "Only need a plain center crop / resize with no subject logic → use ffmpeg-cookbook"
  - "Splitting a long video into many short clips → use long-video-to-shorts (then reframe each here)"
  - "Adding burned-in captions after reframing → use whisper-caption-burn"
  - "Tracking/masking a moving object across frames → use video-object-tracking-sam2"
  - "Just downloading the source clip first → use youtube-download"
keywords: [reframe, 9:16, vertical video, smart crop, 1:1, 4:5, reels, shorts, tiktok, aspect ratio, recrop, portrait crop, subject-aware, auto-reframe, ffmpeg crop, letterbox, blurred background fill, keep face centred]
similar_to: [ffmpeg-cookbook, long-video-to-shorts, whisper-caption-burn, video-object-tracking-sam2, batch-transcode-encode]
inputs_needed:
  - Path to the source horizontal video
  - Target aspect ratio (9:16 vertical, 1:1 square, or 4:5 portrait)
  - Whether to crop (fill the frame, may lose edges) or fit (blurred bars, keep everything)
  - Whether the subject moves a lot (dynamic pan needed) or is roughly static (constant crop is fine)
produces: A re-encoded MP4 at the requested aspect ratio, subject kept in frame
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Social Video Reframe

Recrop landscape footage to a social aspect ratio (9:16 / 1:1 / 4:5) while keeping the
subject in frame. Three tiers, cheapest first: fixed geometric crop → subject-aware
constant crop (bundled script) → AI dynamic pan+zoom (external tool).

## When to use

Pick the smallest tier that works:

- **Tier 1 — geometric crop.** One dominant subject sits near a known spot (centre, or a
  fixed side). A single ffmpeg command. Start here.
- **Tier 2 — subject-aware constant crop.** Subject is off-centre or you're batching many
  clips and don't want to eyeball each. `scripts/smart_reframe.py` samples frames, finds
  the median face/person x, and picks one crop offset. Still no jitter.
- **Tier 3 — dynamic pan+zoom.** Subject moves across the frame (walking, cutting between
  people). Needs a moving virtual camera — use an AI reframer (see Pitfalls).

## Prerequisites

- **ffmpeg (this Mac):** no brew. Use the portable binary from pip `imageio-ffmpeg`:
  `FFMPEG=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")`
  (or the copy at `_research_bank/bin/ffmpeg`). Every command below uses `$FFMPEG`.
- **Tier 2 detector deps:** `python3 -m pip install --user opencv-python numpy imageio-ffmpeg`.
  Face detection falls back Haar-cascade → centre if `mediapipe` isn't installed, so it
  runs even on Python 3.9. `mediapipe` (if it installs) gives better detection.
- Know your source dimensions: `$FFMPEG -hide_banner -i input.mp4` (read the `WxH`).

## Recipes

Set the binary once:

```bash
FFMPEG=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
```

### Tier 1 — geometric crop (centre)

The crop filter is `crop=w:h:x:y`. Compute the widest window of the target AR that fits
the full source height, centred. ffmpeg evaluates the expressions, so you don't do the math:

```bash
# 16:9 -> 9:16 vertical, centred, full height
$FFMPEG -i input.mp4 -vf "crop=ih*9/16:ih:(iw-ih*9/16)/2:0" \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a copy reel_9x16.mp4

# 1:1 square, centred
$FFMPEG -i input.mp4 -vf "crop=ih:ih:(iw-ih)/2:0" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy square.mp4

# 4:5 portrait, centred
$FFMPEG -i input.mp4 -vf "crop=ih*4/5:ih:(iw-ih*4/5)/2:0" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy portrait_4x5.mp4
```

**Bias the crop toward a side** (e.g. speaker sits left-of-centre): replace the `x` term.
`0` = hard left, `iw-ih*9/16` = hard right, or nudge from centre, e.g. `(iw-ih*9/16)/2 - 240`.

**Force exact output pixels** (platforms like clean 1080×1920) by scaling after the crop:

```bash
$FFMPEG -i input.mp4 -vf "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy reel_1080x1920.mp4
```

### Tier 1b — fit (blurred bars, nothing cropped)

When losing the sides is unacceptable, scale the whole frame to fit inside 9:16 and fill the
gaps with a blurred, zoomed copy of itself:

```bash
$FFMPEG -i input.mp4 -filter_complex \
"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30[bg];\
 [0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];\
 [bg][fg]overlay=(W-w)/2:(H-h)/2" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy reel_blurbars.mp4
```

Swap `overlay=(W-w)/2:(H-h)/2` for `overlay=(W-w)/2:100` to lift the video higher and leave
room for a caption strip at the bottom.

### Tier 2 — subject-aware constant crop (bundled script)

Samples frames, finds the dominant face/person, and applies one crop offset so an off-centre
speaker stays framed. No manual x-math, no per-frame jitter:

```bash
python3 scripts/smart_reframe.py input.mp4 reel_9x16.mp4 --ar 9:16
python3 scripts/smart_reframe.py talk.mp4 square.mp4    --ar 1:1  --samples 60
```

It prints the chosen crop, e.g. `source 1920x1080 -> crop 608x1080 @ x=712 (subject cx=1016)`.
Flags: `--ar` (9:16 | 1:1 | 4:5), `--samples` (detection frames, default 30), `--crf`.

**Batch a folder:**

```bash
for f in clips/*.mp4; do
  python3 scripts/smart_reframe.py "$f" "out/$(basename "${f%.*}")_9x16.mp4" --ar 9:16
done
```

### Tier 3 — AI dynamic pan+zoom

For a moving camera that tracks the subject across the frame, don't hand-roll it — use a
scene-aware reframer that drives a smoothed virtual camera and encodes via ffmpeg:

- `KazKozDev/auto-vertical-reframe` — MediaPipe + YOLOv11, per-scene subject ranking, smoothed pan path.
- `kamilstanuch/Autocrop-vertical` — YOLOv8 + PySceneDetect, decides crop-tight vs letterbox per scene.

Clone, install its requirements in a venv, point it at your clip. Reserve for genuinely moving
subjects — for a seated talking head Tier 2 looks steadier.

## Verify

```bash
# Confirm the output aspect ratio / dimensions
$FFMPEG -hide_banner -i reel_9x16.mp4 2>&1 | grep -Eo 'Stream.*Video.*[0-9]{2,4}x[0-9]{2,4}'
# 1080x1920 (or your WxH). 1080/1920 = 0.5625 = 9/16 ✓

# Eyeball the framing: pull three frames and inspect that the subject is inside
$FFMPEG -i reel_9x16.mp4 -vf "fps=1/3" -frames:v 3 check_%02d.png
```

Open the PNGs (or the MP4) and confirm no head/face is clipped and audio is intact.

## Pitfalls

- **Odd dimensions → encoder error.** libx264 needs even width/height. The `crop=ih*9/16`
  expression can land odd; the script rounds down to even. In hand-written commands append
  `,scale=trunc(iw/2)*2:trunc(ih/2)*2` if you hit "height not divisible by 2".
- **`-c:a copy` can fail** if the container/codec mismatches. Fall back to `-c:a aac -b:a 128k`.
- **Source narrower than target crop.** A 4:3 source can't yield a full-height 9:16 without
  going wider than the frame; the script clamps x inside bounds (may leave the subject at an
  edge). Use Tier 1b blurred-bars fit instead when the source is too narrow.
- **Detection finds nothing** (no faces, dark footage) → Tier 2 falls back to centre, same as
  Tier 1. Bump `--samples`, or install `mediapipe` for person/pose cues, or just centre-crop.
- **Jitter from per-frame tracking.** This skill deliberately uses ONE constant crop for
  static subjects — smooth by design. Only reach for Tier 3 when the subject actually moves.
- **Reframe before captions.** Burn captions (whisper-caption-burn) on the already-9:16 file
  so text is sized and placed for the vertical frame, not scaled from a landscape overlay.

## Sources

- [ffmpeg crop filter guide (ffmpeglab)](https://www.ffmpeglab.com/articles/ffmpeg-crop-video.html)
- [auto-vertical-reframe](https://github.com/KazKozDev/auto-vertical-reframe) · [Autocrop-vertical](https://github.com/kamilstanuch/Autocrop-vertical)
