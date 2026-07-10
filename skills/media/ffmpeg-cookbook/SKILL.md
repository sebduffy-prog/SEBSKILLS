---
name: ffmpeg-cookbook
category: media
description: >
  Battle-tested, copy-pasteable ffmpeg recipes with the CORRECT flags for each job:
  losslessly concat/stitch clips, trim/cut without re-encoding, crossfade with xfade +
  acrossfade, burn a logo/watermark overlay, apply a .cube LUT colour grade (lut3d),
  and export a clean high-quality GIF or animated WebP via palettegen/paletteuse.
  Reach for this whenever you need to "join videos", "add a crossfade", "put a watermark
  on a video", "grade with a LUT", "make a GIF from a clip", or "convert MP4 to GIF" —
  it gives the exact command, not vague guidance.
when_to_use:
  - "Stitch several clips into one, ideally without re-encoding"
  - "Add a smooth crossfade/dissolve between two clips (video AND audio)"
  - "Burn a logo or text watermark into the corner of a video"
  - "Apply a .cube LUT / colour grade to footage"
  - "Export a small, clean-looking GIF or animated WebP from a video clip"
  - "Trim/cut a section out of a video quickly"
  - "You know the effect you want but not the exact ffmpeg filter/flags"
when_not_to_use:
  - "Reframe 16:9 → 9:16 with subject tracking → use social-video-reframe"
  - "Auto-remove silent gaps from a talking-head cut → use auto-silence-cut"
  - "Burn transcript subtitles/captions onto video → use whisper-caption-burn"
  - "Pull still frames / thumbnails out at N fps → use video-frame-extraction"
  - "Detect shot/scene boundaries to split on cuts → use shot-scene-detection"
  - "ffmpeg/yt-dlp binary not installed yet → run media-toolchain-bootstrap first"
  - "HDR→SDR tonemap or heavy colour-space work → use hdr-tonemap-color"
keywords: [ffmpeg, concat, crossfade, xfade, acrossfade, overlay, watermark, logo, lut3d, cube lut, colour grade, color grade, gif, palettegen, paletteuse, webp, trim, cut, stitch, join videos, mp4 to gif, ffprobe]
similar_to: [social-video-reframe, hdr-tonemap-color, batch-transcode-encode, whisper-caption-burn, video-clip-extractor, contact-sheet-storyboard]
inputs_needed:
  - "Absolute path(s) to the input clip(s)"
  - "For concat: are the clips the SAME codec/resolution/fps? (decides lossless vs re-encode)"
  - "For crossfade: how many seconds of overlap, and the length of the FIRST clip"
  - "For watermark: logo PNG path + corner + margin/opacity"
  - "For LUT: path to the .cube file"
  - "For GIF: target width and fps (smaller = smaller file)"
produces: A single output video/GIF/WebP file written to a path you specify
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# ffmpeg Cookbook

Exact, verified ffmpeg commands for the six jobs people actually ask for. All commands
tested against ffmpeg 7.1. Pick the recipe, swap paths, run.

## When to use

You want a specific edit done to a video — join, cut, crossfade, watermark, grade, or
GIF-export — and you want the RIGHT invocation the first time (concat has three different
methods; GIF is garbage without a palette; xfade offset trips everyone up).

## Prerequisites (this Mac)

No brew ffmpeg here. Use the portable binary from `imageio-ffmpeg`:

```bash
FF=$(python3 -c "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())")
# ffprobe is NOT bundled with imageio-ffmpeg. If you need it, it may live at
# _research_bank/bin/ffprobe; otherwise derive metadata with $FF -i <file> 2>&1.
"$FF" -version | head -1
```

Every recipe below uses `"$FF"`. If a real `ffmpeg` is on PATH you can use that instead.
Always pass absolute paths for inputs/outputs.

## Recipe 1 — Concat / stitch clips

**Case A: same codec, resolution, fps → lossless, instant (stream copy).**
Make a list file (paths absolute, escape single quotes), then use the concat *demuxer*:

```bash
cat > /tmp/list.txt <<'EOF'
file '/abs/path/clip1.mp4'
file '/abs/path/clip2.mp4'
file '/abs/path/clip3.mp4'
EOF
"$FF" -f concat -safe 0 -i /tmp/list.txt -c copy /abs/out.mp4
```

**Case B: mixed codecs/resolutions/fps → re-encode with the concat *filter*.** Normalise
first (scale + fps + SAR), then concat. Example for two clips to 1080p/30:

```bash
"$FF" -i /abs/a.mov -i /abs/b.mp4 -filter_complex \
"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1,setsar=1,fps=30[v0]; \
 [1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1,setsar=1,fps=30[v1]; \
 [v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]" \
-map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset medium -c:a aac /abs/out.mp4
```

If a clip has no audio, add `-f lavfi -t 0.1 -i anullsrc` or drop `:a=1` and don't map audio.

## Recipe 2 — Trim / cut

**Fast, keyframe-accurate-ish (no re-encode):** put `-ss`/`-to` before `-i`.

```bash
"$FF" -ss 00:00:12 -to 00:00:47 -i /abs/in.mp4 -c copy /abs/clip.mp4
```

**Frame-accurate (re-encode):** put `-ss` after `-i`, or add `-c:v libx264 -crf 18`.

```bash
"$FF" -i /abs/in.mp4 -ss 12.0 -to 47.0 -c:v libx264 -crf 18 -c:a aac /abs/clip.mp4
```

## Recipe 3 — Crossfade two clips (xfade + acrossfade)

`xfade` needs both inputs same size/fps/pixfmt. **`offset` = time in the FIRST clip where
the transition starts = (duration of clip1) − (crossfade duration).** If clip1 is 10s and
you want a 1s dissolve, `offset=9`. Output length = d1 + d2 − duration.

```bash
D=1        # crossfade seconds
OFF=9      # = length_of_clip1 - D
"$FF" -i /abs/a.mp4 -i /abs/b.mp4 -filter_complex \
"[0:v][1:v]xfade=transition=fade:duration=$D:offset=$OFF[v]; \
 [0:a][1:a]acrossfade=d=$D[a]" \
-map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset medium -c:a aac /abs/out.mp4
```

Get clip1's duration to compute OFF:

```bash
"$FF" -i /abs/a.mp4 2>&1 | grep Duration   # HH:MM:SS.xx
```

Transitions include `fade` (0), `dissolve` (25), `fadeblack` (12), `wipeleft` (1),
`slideright` (6), `circleopen` (19), `pixelize` (26) — 58 total (`-h filter=xfade`).
If clips differ, normalise each first as in Recipe 1B before the `[0:v][1:v]xfade`.

## Recipe 4 — Watermark / logo overlay

Bottom-right, 20px margin, logo scaled to 160px wide and 60% opacity:

```bash
"$FF" -i /abs/in.mp4 -i /abs/logo.png -filter_complex \
"[1:v]scale=160:-1,format=rgba,colorchannelmixer=aa=0.6[wm]; \
 [0:v][wm]overlay=W-w-20:H-h-20" \
-c:a copy /abs/out.mp4
```

Corner cheat-sheet for `overlay=x:y`: TL `20:20` · TR `W-w-20:20` ·
BL `20:H-h-20` · BR `W-w-20:H-h-20`. For a **text** watermark instead of a PNG:

```bash
"$FF" -i /abs/in.mp4 -vf \
"drawtext=text='VCCP':x=W-tw-20:y=H-th-20:fontsize=36:fontcolor=white@0.7:box=1:boxcolor=black@0.3:boxborderw=8" \
-c:a copy /abs/out.mp4
```

(`drawtext` needs an available font; add `:fontfile=/System/Library/Fonts/Helvetica.ttc` if it errors.)

## Recipe 5 — Apply a .cube LUT grade (lut3d)

```bash
"$FF" -i /abs/in.mp4 -vf "lut3d=file='/abs/grade.cube':interp=tetrahedral" \
-c:v libx264 -crf 18 -preset medium -c:a copy /abs/graded.mp4
```

`interp` defaults to `tetrahedral` (best quality); `trilinear` is faster. To dial back
the grade, blend with the original: `split[a][b];[b]lut3d=file=...[g];[a][g]blend=all_mode=normal:all_opacity=0.7`.

## Recipe 6 — Clean GIF (or animated WebP)

Never GIF without a palette — it dithers to mud. Two-pass palettegen/paletteuse. Set
width + fps small; those control size the most:

```bash
W=480; FPS=15
"$FF" -i /abs/in.mp4 -vf \
"fps=$FPS,scale=$W:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3" \
-loop 0 /abs/out.gif
```

Trim to a section first with `-ss`/`-to` before `-i` to keep it short. For a **much
smaller** file at similar quality, export animated WebP instead:

```bash
"$FF" -i /abs/in.mp4 -vf "fps=15,scale=480:-1:flags=lanczos" \
-loop 0 -c:v libwebp -lossless 0 -q:v 70 /abs/out.webp
```

## Verify

- Command exits 0 and the output file exists and is non-zero:
  `ls -la /abs/out.*`
- Inspect result metadata: `"$FF" -i /abs/out.mp4 2>&1 | grep -E "Duration|Stream"`.
  - Concat: duration ≈ sum of inputs. Crossfade: duration ≈ d1+d2−D.
- Eyeball a frame without opening a player:
  `"$FF" -i /abs/out.mp4 -vf "select=eq(n\,30)" -vframes 1 /tmp/check.png` then Read it.
- GIF: confirm size is sane (aim <5 MB) and it loops.

## Pitfalls

- **concat demuxer `-c copy` fails / glitches** when inputs differ in codec/res/fps/SAR.
  That's the signal to switch to the concat *filter* (Recipe 1B) and re-encode.
- **xfade offset is NOT the crossfade start in clip2** — it's measured on the timeline of
  clip1: `offset = len(clip1) − duration`. Wrong offset = black gap or hard cut.
- **xfade "Inputs must have same" errors** → clips differ in size/fps/pixfmt; normalise
  each stream (`scale,setsar=1,fps=…,format=yuv420p`) before xfade.
- **`-ss` after `-i`** is frame-accurate but decodes from 0 (slow); **before `-i`** is fast
  but can only cut on keyframes when using `-c copy`.
- **GIF looks banded/muddy** → you skipped palettegen/paletteuse, or width/fps too high.
- **Odd width/height** breaks libx264 (`height not divisible by 2`) → use
  `scale=W:-2` (the `-2` rounds to an even number) not `-1`.
- **No `-pix_fmt yuv420p`** on x264 output can make files that QuickTime/Chrome won't play
  → add `-pix_fmt yuv420p` for maximum compatibility.
- **ffprobe missing** here (imageio ships only ffmpeg) — parse `"$FF" -i file 2>&1` instead,
  or use the ffprobe in `_research_bank/bin` if present.
