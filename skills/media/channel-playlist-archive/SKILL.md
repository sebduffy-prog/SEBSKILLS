---
name: channel-playlist-archive
category: media
description: >
  Bulk-lift a whole YouTube channel or playlist with yt-dlp, using a --download-archive file so
  re-runs SKIP everything already grabbed (perfect for keeping a channel mirror up to date). Use when
  someone says "archive this whole channel", "download the entire playlist", "mirror this creator",
  "grab every video from X", "download new uploads since last time", "back up a playlist", "resume a
  half-finished bulk download", or "only get videos from the last month". Covers incremental dedupe,
  date windows, item ranges, rate-limiting to avoid throttling, and a clean per-channel folder tree.
  Local only, no cloud.
when_to_use:
  - Archive an entire channel or playlist to a local folder in one command
  - Keep a mirror fresh — re-run periodically and only pull NEW uploads, never re-download old ones
  - Resume a bulk download that died partway without re-fetching completed items
  - Grab only videos uploaded in a date window (e.g. last month, since a given date)
  - Download a slice of a big playlist (items 1-50, or every other one)
  - Rate-limit / throttle a big pull so YouTube doesn't 429/403 you
when_not_to_use:
  - Just one video → use youtube-download
  - Only the audio (mp3/m4a) of each item → use video-audio-rip (its batch note), or add -x here
  - Only captions/transcripts in bulk → use youtube-transcript-lift
  - yt-dlp/deno/ffmpeg not installed yet on this Mac → run media-toolchain-bootstrap first
  - Post-download re-encode/trim the whole folder → use batch-transcode-encode or ffmpeg-cookbook
keywords: [yt-dlp, download-archive, channel archive, playlist download, bulk download, mirror channel, incremental, dedupe, break-on-existing, dateafter, datebefore, playlist-items, rate-limit, archive.txt, new uploads, back up playlist, resume download, ytdlp, yt dlp]
similar_to: [youtube-download, video-audio-rip, youtube-transcript-lift, media-toolchain-bootstrap, batch-transcode-encode]
inputs_needed:
  - The channel or playlist URL (channel /videos, /streams, /shorts tab, or a playlist link)
  - Target quality/format (best mp4, a resolution cap, or audio-only) and destination folder
  - Any filters — date window, item range, or "only new since last run"
  - Whether auth is needed (members-only / private channel) → which browser you're logged into
produces: A folder of downloaded videos plus an archive.txt of grabbed video IDs, so re-runs only fetch new items
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Channel / Playlist Archive (yt-dlp, incremental)

Bulk-download a whole channel or playlist and keep it fresh. The core trick is a
**`--download-archive` file**: yt-dlp records every video ID it grabs, and on the next run
skips anything already listed. Point it at a channel monthly and you get only the new uploads.

## When to use

You want **many videos** from one source, mirrored to a folder, and you want re-runs to be cheap
and idempotent. For a single clip use `youtube-download`; for audio-only or transcripts in bulk see
the siblings in `when_not_to_use`.

## Prerequisites (this Mac)

- **yt-dlp** — pip install is DEAD here (Python 3.9 cap + YouTube blocks). Use the standalone
  **`yt-dlp_macos`** binary on `PATH` (set up by `media-toolchain-bootstrap`). Check
  `yt-dlp --version` reads `2026.xx.xx`; if old, `yt-dlp -U` (most "it broke" cases are a stale binary).
- **deno** on `PATH` — yt-dlp's JS runtime for the `nsig`/signature challenge; without it you get
  throttled 403s. `media-toolchain-bootstrap` puts a portable `deno` on PATH. Verify `deno --version`.
- **ffmpeg** — merges best-video+best-audio into one file. No brew here; use the portable binary:
  `FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")`
  then pass `--ffmpeg-location "$FF"` (also mirrored at `_research_bank/bin`).
- **A browser logged into YouTube** — only for members-only / private sources (Recipe E).

## The archive-file pattern (read this first)

- `--download-archive archive.txt` — after each successful item, yt-dlp appends a line like
  `youtube VIDEOID`. On re-run it reads that file and **silently skips** those IDs. Delete the line
  (or the file) to force a re-download.
- Keep **one archive file per source folder** so channels don't cross-contaminate.
- Pair it with `--continue --ignore-errors` so one broken/geo-blocked video doesn't halt the batch.
- Add `--break-on-existing` **only** when the source lists newest-first and you want to stop as soon
  as you hit a video you already have (fastest way to fetch "just the new ones"). Without it, yt-dlp
  walks the whole list but still only downloads the unseen items — safer if uploads aren't strictly
  chronological.

## Recipe A — archive a whole channel (best mp4, incremental)

```bash
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
DEST=~/Media/Archive/CHANNELNAME
mkdir -p "$DEST"

yt-dlp --ffmpeg-location "$FF" \
  --download-archive "$DEST/archive.txt" \
  --continue --ignore-errors \
  -f "bv*+ba/b" -S "res,fps,vcodec:h264,acodec:m4a" --merge-output-format mp4 \
  -o "$DEST/%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s" \
  "https://www.youtube.com/@HANDLE/videos"
```

- Use the channel's **`/videos`** tab for uploads, **`/streams`** for lives, **`/shorts`** for shorts,
  or the plain channel URL to get all tabs. A channel URL with no tab may pull tabs you don't want.
- The `%(upload_date>%Y-%m-%d)s -` prefix keeps the folder sorted chronologically; `[%(id)s]` keeps
  filenames unique and stable (matters for the archive to line up).
- **Re-run the exact same command next month** → only new uploads download.

## Recipe B — a playlist (keep playlist order)

```bash
yt-dlp --ffmpeg-location "$FF" \
  --download-archive "$DEST/archive.txt" \
  --continue --ignore-errors \
  -f "bv*+ba/b" --merge-output-format mp4 \
  -o "$DEST/%(playlist_index)03d - %(title)s [%(id)s].%(ext)s" \
  "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

- `%(playlist_index)03d` zero-pads to preserve playlist order (`001 -`, `002 -`, …).
- If you paste a **watch URL that also carries `&list=`**, add `--yes-playlist` to grab the list (or
  `--no-playlist` to force just that one video).

## Recipe C — only a date window / only recent

```bash
# Uploaded in the last month only
yt-dlp ... --dateafter "today-1month" "URL"

# A fixed window (inclusive), YYYYMMDD
yt-dlp ... --dateafter 20260101 --datebefore 20260630 "URL"
```

- Date formats: `YYYYMMDD` or relative `today-1month` / `today-2weeks` / `now-1year`.
- Combine with the archive file freely — date filter narrows the crawl, archive kills dupes.

## Recipe D — item ranges, audio-only, rate-limiting

```bash
# First 50 items, then items 60 to end, every other one:
yt-dlp ... -I 1:50 "URL"
yt-dlp ... -I 60::2 "URL"

# Audio-only archive (m4a) of a whole channel:
yt-dlp ... -f "ba/b" -x --audio-format m4a \
  -o "$DEST/%(title)s [%(id)s].%(ext)s" "URL"

# Be gentle so YouTube doesn't 429/403 a big pull:
yt-dlp ... --limit-rate 4M --sleep-requests 1 --min-sleep-interval 3 --max-sleep-interval 8 "URL"
```

- `-I` (`--playlist-items`) takes `START:STOP:STEP`, comma lists, and negatives: `-I 1:3,7,-5::2`.
- `--sleep-interval`/`--max-sleep-interval` add a randomized pause **between video downloads**;
  `--sleep-requests` paces metadata calls. Use these when archiving hundreds of items.

## Recipe E — members-only / private channel

```bash
yt-dlp ... --cookies-from-browser safari "URL"
```

- Pulls live cookies; **quit Chrome first** if `--cookies-from-browser chrome` errors on a locked
  cookie DB (Safari usually doesn't lock). Specific profile: `--cookies-from-browser "chrome:Profile 1"`.
- If bulk metadata is slow on a huge channel, add `--lazy-playlist` to start downloading as entries
  arrive instead of after the whole list parses.

## Verify

- Count what landed vs what's recorded:
  `ls "$DEST"/*.mp4 | wc -l` and `wc -l < "$DEST/archive.txt"` (archive lines ≥ files is normal;
  it also logs items skipped by date/geo filters).
- Idempotency check: **run the same command again** — it should finish fast with a burst of
  `has already been recorded in the archive` lines and download nothing new.
- Spot-check a file is a clean container:
  `"$FF" -v error -i "$DEST/SOMEFILE.mp4" -f null - && echo OK`.
- List by date to confirm the window filter worked: `ls "$DEST" | sort | head`.

## Pitfalls

- **Re-downloads everything each run** → you moved/renamed the archive file, or used a different path.
  The archive must be the **same file** every run; keep it in `$DEST`.
- **Whole batch aborts on one bad video** → add `--ignore-errors` (and `--continue` to resume partial
  files). Geo-blocked/deleted/private items are logged and skipped.
- **`--break-on-existing` stopped too early** → the source isn't strictly newest-first (mixed shorts,
  re-ordered playlist). Drop `--break-on-existing`; the archive still prevents dupes, it just crawls
  the full list.
- **Got shorts + streams you didn't want** → target the specific tab URL (`/videos`, `/streams`,
  `/shorts`) instead of the bare channel URL.
- **Throttled to ~50 KB/s or random 403s mid-archive** → the `nsig` challenge isn't solving: check
  `deno --version`, then `yt-dlp -U`. For big pulls also add the Recipe D sleep/limit flags.
- **Filenames collide or truncate** → always keep `[%(id)s]` in `-o`; it's the stable unique key the
  archive relies on. Emoji/`/` in titles are sanitised by yt-dlp automatically.
- **SABR / "Requested format is not available"** across the channel → same fixes as youtube-download
  Recipe D (update, cookies, `--extractor-args "youtube:player_client=default,tv,web_safari"`, or a
  bgutil PO-token provider). See the `youtube-download` skill.
- **pip yt-dlp** — do not `pip install yt-dlp` on this Mac. Use the standalone `yt-dlp_macos` binary.
