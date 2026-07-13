---
name: youtube-transcript-lift
category: media
description: >
  Pull a clean, readable text transcript out of a YouTube (or any yt-dlp-supported)
  video WITHOUT downloading the video. Grabs manual or auto-generated captions with
  yt-dlp, strips the VTT timing tags and the auto-caption rolling-window duplication
  into flowing text, and falls back to local Whisper (faster-whisper / whisper.cpp)
  when a video has no captions at all. Use whenever someone says "get me the transcript
  of this YouTube video", "pull the captions as text", "what does this video say",
  "transcribe this link", "dump the subtitles", or "give me the words from this clip".
when_to_use:
  - '"Get the transcript of a YouTube video" — as clean readable text, no timestamps'
  - Pull a video's auto-generated captions and clean them into paragraphs
  - Grab the manual/uploaded subtitle track and turn it into an .srt or plain .txt
  - Transcribe a captionless video locally (Whisper fallback) with no cloud API
  - Batch-lift transcripts for a list of video URLs to feed a summariser or search
  - Get an SRT with timestamps for a podcast/lecture upload
when_not_to_use:
  - You want the actual video/audio file, not the words → use youtube-download or video-audio-rip
  - You want animated word-by-word TikTok/Reels burned captions → use whisper-caption-burn
  - Caption tooling breaks because binaries aren't installed → run media-toolchain-bootstrap first
  - You need on-screen/hardcoded text read off the pixels (OCR), not spoken audio → use video-ocr-onscreen-text
  - Archiving whole channels/playlists of media → use channel-playlist-archive
keywords: [youtube transcript, transcript, captions, subtitles, auto-captions, cc, vtt, srt, yt-dlp, write-auto-subs, whisper, faster-whisper, whisper.cpp, transcribe video, subtitle download, get transcript, closed captions, speech to text, video to text]
similar_to: [youtube-download, video-audio-rip, whisper-caption-burn, media-toolchain-bootstrap, video-ocr-onscreen-text, channel-playlist-archive]
inputs_needed:
  - The video URL (or a text file of URLs for batch)
  - Desired output — clean plain text (default), timestamped SRT, or both
  - Language if not English (yt-dlp sub-lang / Whisper --language); auto-detect is fine
produces: A .txt transcript (deduped, timestamp-free) and/or a .srt, one per video
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# YouTube Transcript Lift

Turn a video link into **words on a page**. Fast path: yt-dlp already knows how to
fetch the caption track — so we never download the video, just the subtitles, then
clean them. Slow path (no captions exist): pull the audio and run local Whisper.

## When to use

Someone hands you a YouTube URL and wants the transcript — for a summary, a quote,
search, or a doc. Default output is clean paragraphs with no timestamps. Ask if they'd
rather have a timestamped `.srt`.

## Prerequisites (this Mac)

- **yt-dlp** — the pip install is DEAD on this machine (Python 3.9 cap + YouTube blocks).
  Use the standalone binary + portable deno already on PATH:
  ```bash
  yt-dlp_macos --version   # confirm the standalone binary is reachable
  ```
  If it isn't set up, run the **media-toolchain-bootstrap** skill first. (`yt-dlp_macos`
  is the binary name; substitute `yt-dlp` if a plain one is on PATH.)
- **ffmpeg** (only for the Whisper fallback — to extract audio). No brew here:
  ```bash
  FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
  ```
- **Whisper** (fallback only) — `pip install faster-whisper`, or a built `whisper-cli`
  from whisper.cpp with a `ggml-*.bin` model. Only needed when a video has zero captions.
- This skill ships `scripts/vtt2txt.py` — the VTT cleaner (handles the auto-caption
  rolling-window duplication).

## Recipe 1 — captions exist (the common case)

Fetch subtitles only, no video. Prefer **manual** captions, fall back to **auto**:

```bash
YT=yt-dlp_macos            # or: YT=yt-dlp
URL="https://www.youtube.com/watch?v=XXXXXXXXXXX"

$YT --skip-download \
    --write-subs --write-auto-subs \
    --sub-langs "en.*" \
    --sub-format vtt \
    -o "%(title)s.%(ext)s" \
    "$URL"
```

Notes on the flags (verified against current yt-dlp):
- `--write-subs` grabs a human-uploaded track if one exists; `--write-auto-subs` grabs
  the machine one. Passing both = prefer manual, fall back to auto.
- `--sub-langs "en.*"` matches `en`, `en-US`, `en-orig`, etc. Use the real code for
  other languages (e.g. `"es.*"`). List what's available first with `--list-subs`.
- Keep `--sub-format vtt`. **Avoid `json3`/`ttml`/`srv3`** — they hit an
  `_UnsafeExtensionError` in current yt-dlp.

Then clean the `.vtt` into flowing text:

```bash
python3 <skill>/scripts/vtt2txt.py *.en*.vtt > transcript.txt
# one line per caption cue instead of paragraphs:
python3 <skill>/scripts/vtt2txt.py *.en*.vtt --keep-nl > transcript.lines.txt
```

Want a **timestamped SRT** instead of plain text? Let yt-dlp convert directly:

```bash
$YT --skip-download --write-subs --write-auto-subs --sub-langs "en.*" \
    --convert-subs srt -o "%(title)s.%(ext)s" "$URL"
```

`--convert-subs srt` runs the built-in converter (uses ffmpeg for some formats), giving
a proper `.srt`. Keep the SRT for tooling; run `vtt2txt.py` when you want clean prose.

## Recipe 2 — no captions (Whisper fallback)

If Recipe 1 prints `There are no subtitles for the requested languages`, download just
the audio and transcribe locally.

```bash
# 1. audio only (m4a), no video
$YT -x --audio-format m4a -o "audio.%(ext)s" "$URL"

# 2a. faster-whisper (simplest on this Mac)
python3 - <<'PY'
from faster_whisper import WhisperModel
m = WhisperModel("base", device="cpu", compute_type="int8")   # "small"/"medium" = more accurate
segs, info = m.transcribe("audio.m4a", vad_filter=True)
open("transcript.txt","w").write(" ".join(s.text.strip() for s in segs) + "\n")
print("detected language:", info.language)
PY
```

whisper.cpp alternative (needs 16 kHz mono WAV first):

```bash
"$FF" -i audio.m4a -ar 16000 -ac 1 audio.wav
whisper-cli -m models/ggml-base.en.bin -f audio.wav -otxt   # writes audio.wav.txt
```

For long videos, `small` gives a good speed/accuracy balance; `int8` keeps it CPU-friendly.

## Recipe 3 — batch a list of URLs

```bash
$YT --skip-download --write-subs --write-auto-subs --sub-langs "en.*" \
    --sub-format vtt -o "%(title)s.%(ext)s" -a urls.txt
for f in *.en*.vtt; do
  python3 <skill>/scripts/vtt2txt.py "$f" > "${f%.vtt}.txt"
done
```

Add `--sleep-requests 1` (or `--sleep-interval`) on big batches to avoid throttling/bot blocks.

## Verify

- `ls *.vtt` (or `.srt`) — a caption file was actually written.
- `wc -w transcript.txt` — non-trivial word count.
- `head -20 transcript.txt` — reads as sentences, **no** `WEBVTT` header, **no**
  `00:00:0x.xxx` timestamps, and **no** stuttering repeats like
  "so we so we so we". If you see repeats, you skipped `vtt2txt.py` — rerun it.
- Whisper path: check the printed `detected language` matches the video.

## Pitfalls

- **Rolling-window duplication.** Raw YouTube auto-VTT repeats each line word-by-word.
  Never `cat` the VTT and call it a transcript — always pass it through `vtt2txt.py`.
- **`--write-auto-subs` alone won't fetch manual captions**, and `--write-subs` alone
  won't fall back to auto. Pass both.
- **Wrong language code = empty.** `--sub-langs en` misses `en-US`/`en-orig`. Use `"en.*"`,
  and run `--list-subs` when unsure what tracks exist.
- **Bot / 403 / "Sign in to confirm you're not a bot".** YouTube periodically blocks
  yt-dlp. Update the standalone binary (`yt-dlp_macos -U`) and/or pass
  `--cookies-from-browser chrome`. This is expected periodic breakage in 2026.
- **json3/ttml formats error out** (`_UnsafeExtensionError`). Stick to `vtt` then convert.
- **No captions ≠ failure** — it just means Recipe 2. Don't retry Recipe 1 forever.
- **Auto-captions have no punctuation/casing.** For a polished doc, a manual track or a
  Whisper pass (which punctuates) reads far better than cleaned auto-VTT.

## Sources

- [yt-dlp subtitle options](https://github.com/yt-dlp/yt-dlp) (`--write-subs`,
  `--write-auto-subs`, `--sub-langs`, `--sub-format`, `--convert-subs`)
- [whisper.cpp CLI](https://github.com/ggml-org/whisper.cpp) (`whisper-cli -otxt`)
