---
name: video-audio-rip
category: media
description: >
  Rip audio-only files (mp3 / m4a / opus / flac / wav) from a YouTube URL, podcast page,
  or a local video file — with embedded cover art and clean title/artist/album metadata.
  Reach for this whenever someone says "get me the mp3 of this song", "extract the audio
  from this video", "download this podcast as an audio file", "just the audio track",
  "convert this mp4 to mp3", or "pull the sound out of this clip". Uses yt-dlp -x for
  online sources and ffmpeg for local files, and embeds the thumbnail so the file looks
  right in Music/Finder. This is the go-to for AUDIO-ONLY output — not video.
when_to_use:
  - "Rip a song's audio from a YouTube URL as an mp3 or m4a"
  - "Download a podcast episode as an audio file with cover art"
  - "Strip the audio track out of a local .mp4/.mov into mp3/wav"
  - "Convert a downloaded video to an audio-only file with title/artist tags"
  - "Grab lossless audio (flac/wav) from a source for editing"
  - "Split a long mix/DJ set into per-chapter audio tracks"
when_not_to_use:
  - "Want the actual VIDEO file (mp4) downloaded → use youtube-download"
  - "Only need the words/transcript, not the audio → use youtube-transcript-lift or whisper-caption-burn"
  - "yt-dlp / ffmpeg not installed yet → run media-toolchain-bootstrap first"
  - "Separate vocals from instrumental / isolate stems → use stem-separation"
  - "Match/normalise loudness or duck music under VO → use audio-loudness-ducking"
  - "Any general ffmpeg edit that isn't audio extraction → use ffmpeg-cookbook"
keywords: [audio rip, extract audio, yt-dlp -x, extract-audio, mp3, m4a, opus, flac, wav, cover art, embed thumbnail, embed metadata, youtube to mp3, mp4 to mp3, podcast download, audio only, rip song, strip audio, ffmpeg -vn, id3 tags]
similar_to: [youtube-download, ffmpeg-cookbook, stem-separation, audio-loudness-ducking, youtube-transcript-lift, media-toolchain-bootstrap]
inputs_needed:
  - "Source: a URL (YouTube/podcast) OR an absolute path to a local video file"
  - "Target format: mp3 (universal), m4a/aac (Apple), opus (small), flac/wav (lossless)"
  - "Do you want cover art + metadata embedded? (default: yes)"
  - "Output folder/filename (defaults to source title in the current dir)"
produces: An audio-only file (e.g. .mp3/.m4a) with embedded cover art and title/artist metadata
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Video → Audio Rip

Pull an audio-only file out of a URL or a local video, with cover art and tags baked in.
For online sources use `yt-dlp -x`; for local files use `ffmpeg`. Pick a recipe, swap the
paths, run.

## When to use

Someone wants the *sound*, not the video: a song as mp3, a podcast episode, or the audio
track stripped out of a clip they already have — ideally with a thumbnail and clean tags
so it looks right in Music/Finder.

## Prerequisites (this Mac)

- **yt-dlp**: pip install is DEAD here (Python 3.9 cap + YouTube blocks). Use the standalone
  `yt-dlp_macos` binary on PATH, with portable `deno` also on PATH. If either is missing,
  run **media-toolchain-bootstrap** first. Verify: `yt-dlp_macos --version`.
- **ffmpeg + ffprobe**: yt-dlp's `-x` REQUIRES both for conversion + thumbnail embedding.
  Portable binary via pip `imageio-ffmpeg` → `python3 -c "import imageio_ffmpeg,os;print(os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()))"`,
  or use `_research_bank/bin`. Point yt-dlp at it with `--ffmpeg-location <dir>` if it isn't on PATH.
- No brew on this Mac. Everything runs from portable binaries.

Set once per shell so the recipes below are copy-pasteable:

```bash
FFDIR=$(python3 -c "import imageio_ffmpeg,os;print(os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()))")
export PATH="$FFDIR:$PATH"          # puts ffmpeg on PATH for both yt-dlp and direct use
YTDLP=yt-dlp_macos                  # standalone binary
```

## Format cheat-sheet

| Format | Flag value | Use it for |
|--------|-----------|------------|
| mp3    | `mp3`     | Universal, plays anywhere. ID3 cover art. Default choice. |
| m4a    | `m4a`     | Apple/AAC, good quality-per-byte, native to Music.app |
| opus   | `opus`    | Smallest at same quality (voice/podcasts). Poor legacy support. |
| flac   | `flac`    | Lossless, for editing/archival. Big files. |
| wav    | `wav`     | Uncompressed PCM, for DAW import. No tags/cover. |

`--audio-quality`: `0` = best VBR … `10` = worst, **or** a bitrate like `192K`/`320K`.
Default is `5`. For a "good mp3" use `0` (best VBR) or `192K`. (Lossless flac/wav ignore it.)

## Recipe 1 — Song/video from YouTube → mp3 with cover art + tags

```bash
$YTDLP -x --audio-format mp3 --audio-quality 0 \
  --embed-thumbnail --embed-metadata \
  --convert-thumbnails jpg \
  -o "%(title)s.%(ext)s" \
  "https://www.youtube.com/watch?v=XXXX"
```

- `-x` extract audio · `--audio-format mp3` convert · `--audio-quality 0` best VBR.
- `--embed-thumbnail` bakes the video thumbnail in as cover art; `--convert-thumbnails jpg`
  avoids webp cover art that some players (and iTunes) won't show.
- `--embed-metadata` writes title/artist/date/description tags.
- Add `--ffmpeg-location "$FFDIR"` if ffmpeg isn't on PATH.

## Recipe 2 — Best-quality m4a (Apple Music friendly)

```bash
$YTDLP -x --audio-format m4a --audio-quality 0 \
  --embed-thumbnail --embed-metadata \
  -o "%(artist,uploader)s - %(title)s.%(ext)s" \
  "URL"
```

`%(artist,uploader)s` uses the real artist tag when present, else falls back to the channel.

## Recipe 3 — Podcast episode → opus (small) or mp3

```bash
# Small file, ideal for spoken word:
$YTDLP -x --audio-format opus --audio-quality 64K \
  --embed-thumbnail --embed-metadata \
  -o "%(playlist_title|)s%(title)s.%(ext)s" \
  "PODCAST_OR_EPISODE_URL"
```

Podcast RSS pages that are just a direct `.mp3` link don't need yt-dlp — download and tag
with ffmpeg (Recipe 5) or `curl -L -o episode.mp3 "URL"`.

## Recipe 4 — Lossless flac/wav

```bash
$YTDLP -x --audio-format flac --embed-thumbnail --embed-metadata -o "%(title)s.%(ext)s" "URL"
# wav has no tag/cover support — expect a bare PCM file:
$YTDLP -x --audio-format wav -o "%(title)s.%(ext)s" "URL"
```

## Recipe 5 — LOCAL video file → mp3 (ffmpeg, no re-download)

Strip the audio out of a file you already have. `-vn` drops video, `-map a:0` takes the
first audio track.

```bash
# Transcode to 192 kbps mp3:
ffmpeg -i input.mp4 -vn -map a:0 -c:a libmp3lame -q:a 2 output.mp3

# Keep it lossless / no re-encode if the source is already AAC → just copy into .m4a:
ffmpeg -i input.mp4 -vn -map a:0 -c:a copy output.m4a

# To WAV for a DAW:
ffmpeg -i input.mp4 -vn -map a:0 -c:a pcm_s16le output.wav
```

`-q:a 2` is ~190 kbps VBR (scale 0–9, lower = better). Add tags + cover to a local file:

```bash
ffmpeg -i input.mp4 -i cover.jpg -map 0:a -map 1:v -c:a libmp3lame -q:a 2 \
  -metadata title="Song Title" -metadata artist="Artist" \
  -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" \
  output.mp3
```

## Recipe 6 — Split a long mix/DJ set into per-chapter tracks

If the source has YouTube chapters, get one audio file per track:

```bash
$YTDLP -x --audio-format mp3 --audio-quality 0 --split-chapters \
  --embed-metadata --embed-thumbnail \
  -o "chapter:%(section_number)02d - %(section_title)s.%(ext)s" \
  "URL"
```

No chapters? Fall back to timestamp cuts with ffmpeg (see **video-clip-extractor**).

## Verify

```bash
ffprobe -hide_banner output.mp3            # confirms codec, bitrate, duration
ffprobe -show_entries format_tags=title,artist -of default=nw=1 output.mp3   # tags present?
# Cover art embedded? A video stream tagged as attached_pic means yes:
ffprobe -show_streams -select_streams v output.m4a 2>/dev/null | grep -i attached_pic
```

Open in Music.app / QuickLook the file in Finder — a thumbnail + title/artist confirms
the embed worked.

## Pitfalls

- **`-x` needs ffmpeg AND ffprobe.** "ffprobe not found" → pass `--ffmpeg-location "$FFDIR"`
  (that dir must contain both). imageio-ffmpeg ships ffmpeg; if ffprobe is missing use
  `_research_bank/bin`.
- **webp cover art won't display** in iTunes/Music. Always add `--convert-thumbnails jpg`.
- **wav/flac + cover:** WAV can't hold a cover; FLAC can via `--embed-thumbnail` but not
  all players read it.
- **`--audio-quality` is only VBR 0–10 or a bitrate** — `0` is BEST, not worst. Easy to
  get backwards. `320K` forces CBR-ish top bitrate for mp3.
- **`--audio-format best`** (the default) keeps the source codec with NO re-encode — fastest
  and lossless-relative-to-source, but you get whatever the site served (often opus/m4a),
  not necessarily mp3.
- **Copy-audio into a container mismatch fails:** `-c:a copy` into `.mp3` breaks if the
  source track is AAC. Copy into `.m4a`/`.mka`, or transcode with `libmp3lame`.
- **Age/region-gated YouTube** may need `--cookies-from-browser safari` (or `chrome`).
- **Long titles / weird chars** in `-o` templates are fine — yt-dlp sanitises them. Wrap
  the template in quotes so the shell doesn't split it.
