---
name: video-clip-extractor
category: media
description: >
  Grab ONLY the part you want out of a video — a single timestamp range (e.g. just
  2:10–4:05), several ranges at once, every chapter split into its own file, or the
  whole thing minus sponsor/intro/outro segments via SponsorBlock. Works both ways:
  yt-dlp --download-sections to pull a slice straight off YouTube WITHOUT fetching the
  full video, or ffmpeg -ss/-to to cut a slice out of a local file (fast stream-copy or
  keyframe-accurate re-encode). Reach for this whenever someone says "download only the
  middle bit", "just clip 2:10 to 4:05", "cut out this section", "split this by its
  chapters", "trim the first 90 seconds", or "download it but skip the sponsor".
when_to_use:
  - "Download only 2:10–4:05 of a YouTube video, not the whole thing"
  - "Split a local video (or a YouTube one) into one file per chapter"
  - "Cut a single clip out of a local .mp4/.mov by start and end timestamp"
  - "Pull several separate ranges out of one source in a single pass"
  - "Trim off the first N seconds or the last N seconds of a file"
  - "Download a video but automatically remove sponsor/intro/outro (SponsorBlock)"
  - "You need the cut to be frame-accurate, not snapped to the nearest keyframe"
when_not_to_use:
  - "Download the FULL video/audio, no trimming → use youtube-download"
  - "Just the audio track of a clip → use video-audio-rip"
  - "Archive a whole channel or playlist → use channel-playlist-archive"
  - "Auto-remove silent gaps from a talk → use auto-silence-cut"
  - "Detect scene/shot cuts to decide where to split → use shot-scene-detection"
  - "Reframe 16:9 → 9:16 or crop for social → use social-video-reframe"
  - "General join/watermark/LUT/GIF ffmpeg recipe → use ffmpeg-cookbook"
  - "yt-dlp / ffmpeg not installed yet → run media-toolchain-bootstrap first"
keywords: [clip, trim, cut, download-sections, sponsorblock, chapters, split by chapter, keyframe accurate, timestamp range, ss to, yt-dlp sections, extract clip, subclip, partial download, force-keyframes-at-cuts, chapter split]
similar_to: [youtube-download, ffmpeg-cookbook, video-audio-rip, channel-playlist-archive, auto-silence-cut, shot-scene-detection]
inputs_needed:
  - "Source: a YouTube/URL, or an absolute path to a local video file"
  - "What to extract: one time range, several ranges, ALL chapters, or full-minus-sponsor"
  - "Time range(s) as HH:MM:SS or MM:SS (start AND end)"
  - "Frame-accurate cut required, or is nearest-keyframe fine? (accuracy vs speed)"
  - "Output path / folder for the resulting clip(s)"
produces: One or more trimmed video files (a single clip, per-range clips, or one file per chapter)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Video Clip Extractor

Cut just the wanted part. Two engines depending on where the source lives:

- **Remote (YouTube etc.)** → `yt-dlp --download-sections` fetches ONLY the slice you ask
  for, so you never download the full video.
- **Local file** → `ffmpeg -ss/-to` copies or re-encodes just the range.

## When to use

Reach for this over `youtube-download` whenever the ask contains "only", "just", "from
X to Y", "the middle", "by chapter", "trim", "skip the sponsor", or a start/end pair.

## Prerequisites (this Mac)

- **yt-dlp**: pip install is DEAD here (Python 3.9 cap + YouTube blocks). Use the
  standalone `yt-dlp_macos` binary on PATH plus portable `deno` on PATH. See
  `media-toolchain-bootstrap` if `yt-dlp_macos --version` fails.
- **ffmpeg**: no brew on this Mac. Get a portable binary path:
  ```bash
  FFMPEG=$(python3 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
  # or use _research_bank/bin/ffmpeg if present
  ```
  `--download-sections` requires ffmpeg to be findable; point yt-dlp at it with
  `--ffmpeg-location "$(dirname "$FFMPEG")"` if it is not on PATH.

## Recipes

### 1. Download ONLY a time range from YouTube (no full download)

The range regex must be prefixed with `*`. Format `*START-END`, timestamps in
`HH:MM:SS`, `MM:SS`, or seconds.

```bash
# Just 2:10 → 4:05, keyframe-fast (may include a few extra frames at the head)
yt-dlp_macos --download-sections "*2:10-4:05" \
  -o "clip.%(ext)s" "https://youtu.be/VIDEO_ID"

# Frame-accurate cut at the exact boundaries (re-encodes around the cut — slower)
yt-dlp_macos --download-sections "*2:10-4:05" --force-keyframes-at-cuts \
  -o "clip.%(ext)s" "https://youtu.be/VIDEO_ID"
```

- Negative end counts back from the video end: `"*-90-inf"` is NOT valid; use
  `"*0-inf"` for whole video, and a negative START like `"*-30-inf"` grabs the last 30s.
- Pass `--download-sections` multiple times for multiple ranges (each becomes its own
  file when they don't overlap; overlapping/merged behaviour varies, so prefer distinct
  ranges).

### 2. Split a video into ONE FILE PER CHAPTER

yt-dlp treats chapter titles as regex. `.*` matches every chapter and splits on it:

```bash
# Split ALL chapters into separate files:
yt-dlp_macos --split-chapters \
  -o "chapter:%(title)s - %(section_number)02d %(section_title)s.%(ext)s" \
  "https://youtu.be/VIDEO_ID"
```

- `--split-chapters` writes one file per chapter using the `chapter:` output template.
- To split only chapters whose title matches a word, use
  `--download-sections "intro"` (no `*` prefix = chapter-title regex).
- **Local file that already has chapters?** Split with ffmpeg using its embedded
  chapter metadata:
  ```bash
  "$FFMPEG" -i in.mp4 -f ffmetadata meta.txt   # inspect [CHAPTER] start/end (in TIMEBASE units)
  # then cut each chapter with recipe 3 using those start/end seconds
  ```

### 3. Cut a clip out of a LOCAL file

Put `-ss` (start) and `-to` (end) BEFORE `-i` for fast seeking. Stream-copy = instant,
no quality loss, but cuts snap to the nearest keyframe:

```bash
# Fast, lossless, keyframe-snapped
"$FFMPEG" -ss 00:02:10 -to 00:04:05 -i in.mp4 -c copy out.mp4

# Frame-accurate (re-encode). -to here is measured from the -ss point when -ss is before -i,
# so keep both before -i and they are absolute source timestamps:
"$FFMPEG" -ss 00:02:10 -to 00:04:05 -i in.mp4 \
  -c:v libx264 -crf 18 -preset veryfast -c:a aac -movflags +faststart out.mp4
```

- Prefer `-to` (absolute end time) over `-t` (duration) to avoid mental math.
- If stream-copy gives a black/frozen head, the range starts mid-GOP → re-encode.

### 4. Pull SEVERAL ranges from one local source

```bash
for r in "00:00:05-00:00:20" "00:10:00-00:10:30" "00:42:10-00:43:00"; do
  s=${r%-*}; e=${r#*-}
  "$FFMPEG" -ss "$s" -to "$e" -i in.mp4 -c copy "clip_${s//:/}_${e//:/}.mp4"
done
```

### 5. Download full video but REMOVE sponsor / intro / outro (SponsorBlock)

```bash
# Physically cut sponsor, self-promo, intro and outro out of the download:
yt-dlp_macos --sponsorblock-remove "sponsor,selfpromo,intro,outro" \
  -o "%(title)s.%(ext)s" "https://youtu.be/VIDEO_ID"

# Or just MARK them as chapters (keep footage, add navigable markers):
yt-dlp_macos --sponsorblock-mark "all" -o "%(title)s.%(ext)s" "https://youtu.be/VIDEO_ID"
```

- Categories: `sponsor, intro, outro, selfpromo, preview, filler, interaction,
  music_offtopic, poi_highlight`. `default` = `all,-filler`. `-remove` re-encodes.
- Combine with `--download-sections` to slice a range AND strip its sponsors.

## Verify

- **Ran correctly?** Check the cut length and that it's not truncated:
  ```bash
  "$FFMPEG" -i out.mp4 2>&1 | grep Duration     # confirm it matches your range
  # or precise seconds:
  FFPROBE=${FFMPEG%ffmpeg}ffprobe
  "$FFPROBE" -v error -show_entries format=duration -of csv=p=0 out.mp4
  ```
- **Chapter split?** `ls` the output folder — expect N files, one per chapter, with
  chapter titles in the names.
- **Frame accuracy needed?** Scrub the first/last second; if you used `-c copy` and the
  head is frozen/black, redo with `--force-keyframes-at-cuts` (yt-dlp) or a re-encode
  (ffmpeg).

## Pitfalls

- **Forgetting the `*`**: `--download-sections "2:10-4:05"` is read as a *chapter title
  regex* and matches nothing. Time ranges MUST be `"*2:10-4:05"`.
- **`-ss` placement**: after `-i` it decodes-then-seeks (slow but accurate); before `-i`
  it seeks fast. With `-c copy` accuracy is keyframe-bound either way — use
  `--force-keyframes-at-cuts` / re-encode when you need exact boundaries.
- **yt-dlp still downloads a lot**: with `--download-sections` on some formats it must
  fetch to a nearby keyframe; this is expected and still far less than the full video.
- **`--sponsorblock-remove` re-encodes** the whole video (slow, quality hit). Use
  `--sponsorblock-mark` if you only want markers.
- **pip yt-dlp will fail** on this Mac — always call `yt-dlp_macos`, not `yt-dlp`.
