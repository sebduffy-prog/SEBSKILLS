---
name: youtube-download
category: media
description: >
  Download a YouTube (or any yt-dlp-supported) video to a local file with robust format/resolution
  choice, and survive 2026-era breakage: SABR-only formats, missing PO-token 403s, age-gates,
  and members/private clips. Use when someone says "download this YouTube video", "grab the 1080p
  mp4", "yt-dlp keeps failing / 403 / SABR", "download an age-restricted video", "get just the
  4K/60fps stream", "rip a talk to watch offline", or "yt-dlp says requested format not available".
  Covers format selection (-f/-S), --cookies-from-browser, PO-token provider setup, and client
  fallbacks. Local only, no cloud.
when_to_use:
  - Download a whole YouTube video at best quality as a single playable mp4/mkv
  - Pull a specific resolution/codec/fps (e.g. exactly 1080p H.264, or 4K60 VP9/AV1)
  - yt-dlp fails with "Requested format is not available", HTTP 403, or "forcing SABR streaming"
  - Grab an age-restricted, members-only, or private/unlisted video you can access in a browser
  - Update a stale yt-dlp that stopped working after a YouTube change
  - Download from Vimeo/Twitter/TikTok/etc. via the same yt-dlp workflow
when_not_to_use:
  - Only need the audio track (mp3/m4a) → use video-audio-rip
  - Only need the captions/transcript text → use youtube-transcript-lift
  - Downloading a whole channel or playlist in bulk with an archive file → use channel-playlist-archive
  - yt-dlp/deno/ffmpeg not installed yet on this Mac → run media-toolchain-bootstrap first
  - Post-download transcode/trim/re-mux questions → use ffmpeg-cookbook or batch-transcode-encode
keywords: [yt-dlp, youtube download, youtube-dl, download video, 1080p, 4k, sabr, po token, pot provider, bgutil, 403 forbidden, age restricted, cookies-from-browser, requested format not available, mp4, mkv, player_client, offline video, yt dlp, ytdlp]
similar_to: [video-audio-rip, youtube-transcript-lift, channel-playlist-archive, media-toolchain-bootstrap, ffmpeg-cookbook]
inputs_needed:
  - The video URL (or a list of URLs)
  - Target quality/format — best, a specific resolution (e.g. 1080p), codec (H.264 vs VP9/AV1), or container (mp4 vs mkv)
  - Whether it needs auth (age-restricted / members / private) → which browser you're logged into YouTube on
produces: A local .mp4/.mkv video file (best or requested format), merged audio+video, in the target folder
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# YouTube Download (yt-dlp, hardened)

Download a video to a local file with the format you actually want, and get past the
2026 YouTube defences (SABR-only manifests, PO-token 403s, age-gates). `yt-dlp` is the
engine; the tricks below are what keep it working.

## When to use

You want the **video file** — whole clip, chosen resolution/codec, playable offline. If you
only want the audio, the transcript, or a whole playlist, use the sibling skill named in
`when_not_to_use` instead.

## Prerequisites (this Mac)

- **yt-dlp** — pip install is DEAD here (Python 3.9 cap + YouTube blocks). Use the standalone
  **`yt-dlp_macos`** binary (installed as `~/.local/bin/yt-dlp` by `media-toolchain-bootstrap`).
  Resolve it once and use `"$YTDLP"` in every command (PATH may not include it):
  `YTDLP="${YTDLP:-$HOME/.local/bin/yt-dlp}"`. Sanity-check:
  `"$YTDLP" --version` (should read like `2026.xx.xx`). If it's old, **update first** — most
  "it broke" reports are a stale binary:
  `"$YTDLP" -U` (or grab the latest release binary again). When even that lags a YouTube change,
  use the nightly channel: `"$YTDLP" --update-to nightly`.
- **deno** on `PATH` — yt-dlp uses it as the JS runtime to solve YouTube's `nsig`/signature
  challenge (without a working JS interp you get throttled 403s or no formats). `media-toolchain-bootstrap`
  puts a portable `deno` on PATH. Verify: `deno --version`.
- **ffmpeg** — needed to **merge** the separate best-video + best-audio streams into one file.
  No brew here; use the portable binary and point yt-dlp at it:
  `FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")`
  then pass `--ffmpeg-location "$FF"` (also mirrored at `_research_bank/bin`).
- **A browser logged into YouTube** — only needed for age-restricted / members / private clips
  (see Recipe C). Chrome or Safari both work with `--cookies-from-browser`.

## Recipe A — best quality, single mp4 (the default ask)

```bash
YTDLP="${YTDLP:-$HOME/.local/bin/yt-dlp}"   # standalone yt-dlp_macos binary
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
"$YTDLP" --ffmpeg-location "$FF" \
  -f "bv*+ba/b" \
  -S "res,fps,vcodec:h264,acodec:m4a" \
  --merge-output-format mp4 \
  -o "%(title)s [%(id)s].%(ext)s" \
  "URL"
```

- `-f "bv*+ba/b"` = best video + best audio, falling back to a best pre-muxed stream.
- `-S "...vcodec:h264..."` = **prefer H.264/m4a** so the result is a universally playable mp4
  (QuickTime, iMovie, PowerPoint). Drop the codec prefs to let true-best (often VP9/AV1) win.
- `--merge-output-format mp4` forces an mp4 container; use `mkv` if you keep VP9/AV1/Opus.

## Recipe B — a specific resolution / codec / fps

```bash
# Exactly 1080p (or the best at/below 1080p), H.264, into mp4
"$YTDLP" --ffmpeg-location "$FF" \
  -S "res:1080,fps,vcodec:h264" --merge-output-format mp4 \
  -o "%(title)s.%(ext)s" "URL"

# True 4K60, keep VP9/AV1, into mkv
"$YTDLP" --ffmpeg-location "$FF" \
  -f "bv*[height<=2160]+ba/b" -S "res,fps" --merge-output-format mkv "URL"
```

- **Prefer `-S` sorting over hard `-f height=1080`** — `-S "res:1080"` picks the closest
  available instead of erroring when an exact rung is missing.
- **Inspect first** when unsure what exists: `"$YTDLP" -F "URL"` lists every format id, codec,
  resolution and note. Then either sort with `-S` or pick ids: `-f 137+140`.

## Recipe C — age-restricted / members-only / private

```bash
# Reuse your logged-in browser session (no manual cookie export)
"$YTDLP" --ffmpeg-location "$FF" \
  --cookies-from-browser safari \
  -f "bv*+ba/b" --merge-output-format mp4 "URL"
```

- `--cookies-from-browser chrome` / `safari` / `firefox` / `edge` — pulls live cookies.
  **Close Chrome first** if it errors on a locked cookie DB (Safari usually doesn't lock).
- For a specific profile: `--cookies-from-browser "chrome:Profile 1"`.
- Alternative: export a `cookies.txt` (a browser extension) and pass `--cookies cookies.txt`.
- Cookies also help ordinary videos: they let yt-dlp use account-bound clients that dodge some
  SABR/403 walls.

## Recipe D — SABR / PO-token / 403 escape hatches

Symptoms: `Requested format is not available`, `HTTP Error 403: Forbidden`,
`YouTube is forcing SABR streaming for this client`, or only tiny/storyboard formats appear.

Try in order (cheapest first):

```bash
# 1. UPDATE — fixes the majority of sudden breakage.
"$YTDLP" -U        # or: "$YTDLP" --update-to nightly

# 2. Add cookies (Recipe C) — unlocks account-bound clients.

# 3. Switch player clients explicitly. Different clients expose non-SABR formats.
"$YTDLP" --extractor-args "youtube:player_client=default,tv,web_safari" \
  --ffmpeg-location "$FF" -f "bv*+ba/b" --merge-output-format mp4 "URL"

# 4. Allow formats that need a PO token (accept the risk of throttling/403 on some):
"$YTDLP" --extractor-args "youtube:formats=missing_pot" \
  --ffmpeg-location "$FF" -f "bv*+ba/b" "URL"
```

**Proper fix — a PO Token provider plugin** (needed reliably for many high-res GVS formats in
2026). Install the maintained **bgutil** provider so yt-dlp mints tokens automatically:

```bash
# Plugin + its token server (Docker is the least-fuss backend)
"$YTDLP" --update-to nightly
python3 -m pip install --user bgutil-ytdlp-pot-provider   # yt-dlp plugin side
docker run -d --name bgutil -p 4416:4416 brainicism/bgutil-ytdlp-pot-provider  # token server
# then just run yt-dlp normally — it auto-detects the provider on localhost:4416
"$YTDLP" --ffmpeg-location "$FF" -f "bv*+ba/b" --merge-output-format mp4 "URL"
```

- The plugin route is the yt-dlp-maintainer-recommended answer; manual `po_token=` values are
  discouraged now (they bind to one video and expire fast).
- If you can't run the provider, cookies (Recipe C) + a fresh nightly + a client switch clears
  most cases.

## Verify

- Exit code 0 and a `[Merger] Merging formats into "…mp4"` (or a `has already been downloaded`)
  line in the output.
- Confirm the file is real and complete:
  `"$FF" -v error -i "OUTPUT.mp4" -f null - && echo OK` (no errors = clean container).
- Check you got the resolution you asked for:
  `"$FF" -i "OUTPUT.mp4" 2>&1 | grep -Eo 'Video: .*[0-9]{3,4}x[0-9]{3,4}'`.
- Preview a frame: `"$FF" -ss 5 -i "OUTPUT.mp4" -frames:v 1 -y check.png`.

## Pitfalls

- **"Requested format is not available"** → almost always a stale binary or SABR. `"$YTDLP" -U`
  first, then Recipe D. Don't hand-pick `-f 137` blindly; run `-F` to see what truly exists.
- **Video and audio downloaded but no merge / two files** → ffmpeg not found. Pass
  `--ffmpeg-location "$FF"`.
- **Result won't open in QuickTime/PowerPoint** → it's VP9/AV1/Opus in mkv/webm. Re-run with the
  H.264 `-S` prefs in Recipe A + `--merge-output-format mp4`, or transcode via ffmpeg-cookbook.
- **`--cookies-from-browser chrome` fails ("could not copy cookie database")** → Chrome is open and
  locking the DB. Quit Chrome, or use `--cookies-from-browser safari`, or export `cookies.txt`.
- **Throttled to ~50 KB/s or random 403s mid-download** → the `nsig` challenge isn't being solved:
  check `deno --version` is on PATH, then update yt-dlp.
- **pip yt-dlp** — do not `pip install yt-dlp` on this Mac (Python 3.9 cap + it gets blocked). Use
  the standalone `yt-dlp_macos` binary from media-toolchain-bootstrap.
- **Filenames with `/`, emoji, or huge titles** → keep the `[%(id)s]` in `-o` for a stable unique
  name, or use `-o "%(id)s.%(ext)s"`.
- **Bulk / playlists** → a single-video command with a playlist URL will grab the whole list.
  For real archiving (`--download-archive`, rate limits, naming trees) use channel-playlist-archive.
