---
name: batch-transcode-encode
category: media
description: >
  Batch-transcode a whole FOLDER of videos to clean H.264/H.265 MP4, or make lightweight
  editing PROXIES, with the RIGHT codec + quality choice every time. Covers the CRF vs
  bitrate decision, x264/x265 presets, hardware acceleration (Apple VideoToolbox on this
  Mac, NVENC on NVIDIA boxes), web-ready deliverables (faststart + yuv420p), and a parallel
  batch loop. Reach for this whenever you need to "convert a folder to mp4", "compress
  these videos", "make edit proxies", "shrink/re-encode footage", "batch transcode", or
  "encode for web/upload" — it gives exact commands, not vague guidance.
when_to_use:
  - "Batch-convert a whole folder of mixed clips (.mov/.mkv/.avi) to H.264 MP4"
  - "Compress big footage to a smaller web/upload deliverable without it looking bad"
  - "Make lightweight, fast-scrubbing editing proxies from heavy 4K/ProRes source"
  - "Transcode to H.265/HEVC for a ~50% smaller file at the same quality"
  - "Use the GPU (VideoToolbox / NVENC) to encode fast instead of slow CPU x264"
  - "You know you need to re-encode but aren't sure CRF vs bitrate, or which preset"
when_not_to_use:
  - "Single one-off edit (concat/trim/watermark/LUT/GIF) → use ffmpeg-cookbook"
  - "Reframe 16:9 → 9:16 with subject tracking → use social-video-reframe"
  - "Just pull the audio track out → use video-audio-rip"
  - "Upscale/restore low-res footage with AI → use ai-upscale-restore"
  - "HDR → SDR tonemap / colour-space conversion → use hdr-tonemap-color"
  - "ffmpeg binary not installed yet → run media-toolchain-bootstrap first"
keywords: [transcode, batch encode, re-encode, convert to mp4, compress video, h264, h265, hevc, libx264, libx265, crf, bitrate, preset, videotoolbox, nvenc, hardware acceleration, proxies, editing proxy, prores, faststart, web video, ffmpeg batch, shrink video]
similar_to: [ffmpeg-cookbook, social-video-reframe, hdr-tonemap-color, ai-upscale-restore, video-audio-rip]
inputs_needed:
  - "Path to the input folder (or single file) and where to write outputs"
  - "Target: web deliverable (small), edit proxy (fast to scrub), or archival (high quality)?"
  - "Codec preference: H.264 (max compatibility) or H.265/HEVC (~50% smaller)?"
  - "Any hard constraints — max file size / target bitrate, or keep resolution vs downscale?"
produces: Re-encoded MP4 file(s) written to your output folder (one per input for batch)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Batch Transcode & Encode

Turn a pile of heavy/mixed video into clean, right-sized MP4 — the correct codec, quality
mode and preset for the job, one file or a whole folder. Commands verified against ffmpeg 7.1.

## When to use

You need to *re-encode* (not just cut/join) — compress for web, standardise a messy folder
to one codec, or generate proxies an editor can actually scrub. This skill exists to stop
the two classic mistakes: encoding to a fixed bitrate when you wanted quality (CRF), and
burning hours on CPU x264 when the GPU would do it in minutes.

## Prerequisites (this Mac)

No brew ffmpeg here. Use the portable binary from `imageio-ffmpeg`:

```bash
FF=$(python3 -c "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())")
"$FF" -version | head -1
```

Every recipe uses `"$FF"`. If a real `ffmpeg` is on PATH, use that. Always pass absolute paths.

**Hardware note:** this Mac has **Apple VideoToolbox** (`h264_videotoolbox` /
`hevc_videotoolbox`) — GPU encode, 5–10× faster than CPU. It does NOT have NVENC (that's
NVIDIA/Linux/Windows; syntax given below for portability). Confirm what your build offers:

```bash
"$FF" -hide_banner -encoders | grep -Ei "videotoolbox|nvenc|libx26"
```

## The one decision: CRF (quality) vs bitrate (size)

- **CRF = constant quality, variable size.** Pick a quality; ffmpeg spends whatever bits
  it takes. This is what you want 90% of the time (web, proxies, archive).
  - `libx264`: CRF **18** visually lossless · **23** default/good · **28** small.
  - `libx265`: CRF **24–28** ≈ x264's 18–23 (HEVC is ~half the size at equal quality).
- **Bitrate = predictable size, variable quality.** Use ONLY when you have a hard size/bandwidth
  cap (e.g. "must be under 10 MB" or a streaming ladder). Prefer 2-pass for accuracy.
- **preset** trades encode speed for compression efficiency (`ultrafast`…`veryslow`).
  `medium` is the default; `slow`/`veryslow` = smaller files, more time; `veryfast` = proxies.

Rule of thumb: **CRF + preset for quality jobs; `-b:v` (2-pass) only for a strict size target.**

## Recipe 1 — Single file, web-ready H.264 (safe default)

```bash
"$FF" -i /abs/in.mov \
  -c:v libx264 -crf 23 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart \
  /abs/out.mp4
```

`-movflags +faststart` moves the index to the front so it streams/plays before fully
downloading. `-pix_fmt yuv420p` guarantees QuickTime/Chrome/PowerPoint can play it.

## Recipe 2 — H.265 / HEVC (~50% smaller, same look)

```bash
"$FF" -i /abs/in.mov \
  -c:v libx265 -crf 26 -preset medium -pix_fmt yuv420p \
  -tag:v hvc1 -c:a aac -b:a 128k -movflags +faststart \
  /abs/out_hevc.mp4
```

`-tag:v hvc1` is REQUIRED for Apple/QuickTime to recognise the HEVC stream — without it the
file plays as a black/green screen in QuickTime and Safari. Great for archive/storage; for
*broad web upload* H.264 (Recipe 1) is still the most universally compatible.

## Recipe 3 — Hardware-accelerated (fast) encode

**Apple VideoToolbox (this Mac).** Uses `-q:v` (quality, 1–100, higher = better) on Apple
Silicon, or `-b:v` for a bitrate target:

```bash
# H.264, quality mode
"$FF" -i /abs/in.mov \
  -c:v h264_videotoolbox -q:v 60 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart /abs/out.mp4

# H.265/HEVC, bitrate target (needs the hvc1 tag like Recipe 2)
"$FF" -i /abs/in.mov \
  -c:v hevc_videotoolbox -b:v 6M -tag:v hvc1 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart /abs/out_hevc.mp4
```

VideoToolbox trades some efficiency for huge speed — files are a bit larger than libx265 at
equal quality, and default quality can look hazy, so don't set `-q:v` too low (start ~55–65).
For maximum quality-per-byte, use CPU x264/x265 (Recipes 1–2) instead.

**NVENC (NVIDIA machines, not this Mac)** — same idea, different flags:

```bash
ffmpeg -i in.mov -c:v h264_nvenc -rc vbr -cq 23 -preset p5 \
  -pix_fmt yuv420p -c:a aac -movflags +faststart out.mp4   # -c:v hevc_nvenc for HEVC
```

## Recipe 4 — Editing proxies (fast to scrub, downscaled)

Proxies are meant to be light and instantly seekable, not pretty. Downscale to 1280-wide,
all-intra-ish fast preset, keep timecode/duration identical to source so they relink:

```bash
"$FF" -i /abs/in.mov \
  -vf "scale=1280:-2" \
  -c:v libx264 -crf 24 -preset veryfast -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart \
  /abs/proxies/in_proxy.mp4
```

`scale=1280:-2` keeps aspect and forces an **even** height (x264 requires it). On this Mac
you can also proxy with `-c:v h264_videotoolbox -q:v 50` for near-instant GPU proxies.
(Prefer ProRes proxies for a pro NLE? `-c:v prores_ks -profile:v 0` — bigger but edit-friendly.)

## Recipe 5 — Batch a whole folder

Loop every video in a folder → matching `.mp4` in an output folder. Skips files already done
(safe to re-run). Adjust the codec block to any recipe above:

```bash
IN=/abs/input_folder
OUT=/abs/output_folder
mkdir -p "$OUT"
shopt -s nullglob nocaseglob
for f in "$IN"/*.{mov,mp4,mkv,avi,m4v,webm}; do
  base=$(basename "${f%.*}")
  dest="$OUT/$base.mp4"
  [ -f "$dest" ] && { echo "skip $base"; continue; }
  echo ">> $base"
  "$FF" -hide_banner -loglevel error -stats -i "$f" \
    -c:v libx264 -crf 23 -preset medium -pix_fmt yuv420p \
    -c:a aac -b:a 128k -movflags +faststart "$dest" \
    && echo "ok $base" || echo "FAIL $base"
done
```

**Run encodes in parallel** (CPU x264 is single-job-hungry, but proxies/HW encodes parallelise
well). With GNU `xargs` (`-P` = jobs); keep it to ~half your cores for CPU encodes:

```bash
ls "$IN"/*.mov | xargs -P 3 -I{} sh -c \
  '"$0" -hide_banner -loglevel error -i "$1" -c:v h264_videotoolbox -q:v 60 \
   -pix_fmt yuv420p -c:a aac -movflags +faststart \
   "'"$OUT"'/$(basename "${1%.*}").mp4"' "$FF" {}
```

## Recipe 6 — Hard size cap (2-pass bitrate)

Only when a file MUST fit a limit. Target bitrate ≈ (target_MB × 8192) / duration_seconds −
audio_kbps. Two passes hit the size accurately:

```bash
BV=5M   # video bitrate for your size budget
"$FF" -y -i /abs/in.mov -c:v libx264 -b:v $BV -preset medium -pass 1 -an -f null /dev/null && \
"$FF" -i /abs/in.mov -c:v libx264 -b:v $BV -preset medium -pass 2 \
  -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart /abs/out.mp4
rm -f ffmpeg2pass-*.log*
```

## Verify

- Command exits 0 and each output exists and is non-zero: `ls -la /abs/output_folder`.
- Compare sizes to prove compression worked:
  `du -h /abs/in.mov /abs/out.mp4`.
- Inspect codec/duration/pixfmt: `"$FF" -i /abs/out.mp4 2>&1 | grep -E "Duration|Stream"`.
  Duration should match source; video line should show `h264`/`hevc` + `yuv420p`.
- Confirm faststart (index at front) for web:
  `"$FF" -v trace -i /abs/out.mp4 2>&1 | grep -m1 -i "moov" ` should appear early.
- Eyeball a frame without a player:
  `"$FF" -i /abs/out.mp4 -vf "select=eq(n\,60)" -vframes 1 /tmp/check.png` then Read it.
- Batch: count matches — `ls /abs/input_folder | wc -l` vs `ls /abs/output_folder | wc -l`.

## Pitfalls

- **CRF vs bitrate mix-up** — setting `-b:v` when you wanted quality gives bloated or ugly
  files; setting CRF when you needed a size cap gives unpredictable sizes. Pick per the
  decision box above.
- **HEVC plays black in QuickTime/Safari** → you forgot `-tag:v hvc1`. Always add it for
  `libx265` / `hevc_videotoolbox` MP4s.
- **VideoToolbox output looks hazy / blocky** → `-q:v` too low; raise to ~60–70, or use CPU
  x264/x265 for quality-critical work. HW encoders prioritise speed over efficiency.
- **`height not divisible by 2`** on scaled output → use `scale=W:-2` (even-rounding), never `-1`.
- **No `-pix_fmt yuv420p`** → some players (QuickTime, PowerPoint) refuse the file, especially
  from 10-bit or 4:2:2 source. Always force it for deliverables.
- **File won't stream / long spinner before play** → add `-movflags +faststart`.
- **NVENC flags on this Mac** → `h264_nvenc` isn't in this build; use `*_videotoolbox`.
- **2-pass leaves `ffmpeg2pass-*.log`** in the working dir → `rm` them after (shown above).
- **`nocaseglob`/`nullglob` are bash** — run the batch loop in bash, and if a glob matches
  nothing, `nullglob` stops it iterating the literal pattern.
