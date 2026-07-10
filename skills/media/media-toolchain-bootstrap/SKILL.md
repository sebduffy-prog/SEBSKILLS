---
name: media-toolchain-bootstrap
category: media
description: >
  One-shot macOS setup or repair of the local media toolchain WITHOUT Homebrew or sudo:
  installs the standalone yt-dlp_macos binary, a portable Deno JS runtime (yt-dlp needs it
  to solve YouTube's n-sig / player challenges), and a portable ffmpeg via the imageio-ffmpeg
  wheel. Run this FIRST whenever "yt-dlp is broken", "yt-dlp not found", downloads fail with
  nsig/player errors, "ffmpeg not installed", "set up ffmpeg without brew", or any other
  media skill can't find its binaries. It's the fix-it button for the whole download+encode
  toolchain on this Mac. Produces working yt-dlp, deno and ffmpeg on PATH.
when_to_use:
  - "yt-dlp is broken / 'command not found' / pip yt-dlp won't install or run"
  - "YouTube downloads fail with nsig, n-parameter, or 'unable to extract player' errors"
  - "You need ffmpeg but there's no Homebrew on this Mac"
  - "Another media skill (youtube-download, ffmpeg-cookbook, whisper-caption-burn) reports a missing binary"
  - "First-time setup of the download + transcode toolchain on a fresh machine"
  - "yt-dlp works but is out of date and YouTube changed its player again"
when_not_to_use:
  - "Binaries already work and you just want to download a video → use youtube-download"
  - "You just need a transcript, not the toolchain → use youtube-transcript-lift"
  - "You want a specific ffmpeg edit (concat/crossfade/GIF) → use ffmpeg-cookbook"
  - "Local speech-to-text install (whisper) → use whisper-caption-burn"
  - "Bulk-encode/transcode files, binaries already present → use batch-transcode-encode"
keywords: [yt-dlp, yt-dlp_macos, deno, ffmpeg, imageio-ffmpeg, bootstrap, install, setup, repair, fix yt-dlp, nsig, n-parameter, player challenge, no brew, no homebrew, macos, toolchain, path, portable binary]
similar_to: [youtube-download, ffmpeg-cookbook, whisper-caption-burn, batch-transcode-encode, channel-playlist-archive]
inputs_needed:
  - "Nothing required — it self-installs. Optionally: a target bin dir (default ~/.local/bin via MEDIA_BIN_DIR)"
  - "Confirm the user is on macOS (this skill is macOS-specific)"
produces: Working yt-dlp, deno and ffmpeg binaries on PATH (default ~/.local/bin)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Media Toolchain Bootstrap (macOS)

Get `yt-dlp`, `deno` and `ffmpeg` working on this Mac in one shot — no Homebrew, no
sudo. This is the prerequisite every other download/encode media skill depends on, and
the repair button when yt-dlp breaks (which it does whenever YouTube changes its player).

## When to use

- yt-dlp is missing or broken, or downloads fail with `nsig` / n-parameter / "unable to
  extract player" errors.
- ffmpeg isn't installed and there's no brew.
- A sibling skill complains it can't find a binary.

## Why these three (this Mac's constraints)

- **yt-dlp via pip is DEAD here** — the system Python is capped at 3.9 and pip-installed
  yt-dlp gets blocked by YouTube. Use the prebuilt **`yt-dlp_macos`** standalone binary
  from GitHub releases instead. It bundles its own Python, so 3.9 doesn't matter.
- **Deno is required, not optional.** Modern yt-dlp must run JavaScript to solve YouTube's
  n-sig / player challenges. Without a JS runtime (Deno / Node / Bun / QuickJS) you get
  throttled ~50 KB/s downloads or "unable to extract" failures. We install portable Deno.
- **ffmpeg via `imageio-ffmpeg`** — a pip wheel that ships a portable ffmpeg binary
  (`imageio_ffmpeg.get_ffmpeg_exe()`), so no brew/LibreOffice needed. Also mirrored at
  `_research_bank/bin`.

## Fast path (recommended)

Run the bundled script — idempotent, safe to re-run to upgrade/repair:

```bash
bash /Users/seb.duffy/Documents/GitHub/SEBSKILLS/skills/media/media-toolchain-bootstrap/scripts/bootstrap.sh
```

Then make sure the bin dir is on PATH for this session (the script prints the exact line):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Manual steps (if you prefer, or the script fails)

### 1. yt-dlp — standalone macOS binary

```bash
mkdir -p ~/.local/bin
curl -fL --retry 3 \
  https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos \
  -o ~/.local/bin/yt-dlp
chmod +x ~/.local/bin/yt-dlp
```

To **update** an existing install later, prefer the self-updater (works on the binary):

```bash
yt-dlp -U        # or: yt-dlp --update-to stable
```

### 2. Deno — portable JS runtime (fixes nsig / throttling)

```bash
export DENO_INSTALL="$HOME/.deno"
curl -fsSL https://deno.land/install.sh | sh -s -- -y
ln -sf "$DENO_INSTALL/bin/deno" ~/.local/bin/deno
```

yt-dlp auto-detects `deno` on PATH — no extra flag needed. (If you ever need to force it:
`--extractor-args "youtube:player_client=default"` plus a runtime on PATH.)

### 3. ffmpeg — portable via imageio-ffmpeg

```bash
python3 -m pip install --user --upgrade imageio-ffmpeg
FFMPEG=$(python3 -c 'import imageio_ffmpeg as f; print(f.get_ffmpeg_exe())')
ln -sf "$FFMPEG" ~/.local/bin/ffmpeg
```

If pip refuses due to an externally-managed environment, add `--break-system-packages`.

## Verify

Each of these should print a version, not "command not found":

```bash
yt-dlp --version      # e.g. 2026.06.xx
deno --version        # deno 2.x.x
ffmpeg -version | head -1
```

End-to-end smoke test — this exercises the exact path that breaks without Deno (the n-sig
solve). It should finish fast at full speed, not throttle:

```bash
yt-dlp -f "best[height<=360]" -o /tmp/ytdlp_smoke.%(ext)s \
  "https://www.youtube.com/watch?v=jNQXAC9IWoU" && ls -lh /tmp/ytdlp_smoke.*
```

## Pitfalls

- **Downloads crawl at ~50 KB/s or "unable to extract player"** → Deno isn't on PATH.
  Re-run step 2 and confirm `deno --version`. This is the #1 cause of "yt-dlp is broken".
- **`yt-dlp: command not found` in a new shell** → `~/.local/bin` isn't on PATH. Add
  `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` to persist it.
- **Wrong binary**: don't grab `yt-dlp` (Linux/generic) or `yt-dlp_macos_legacy` (that's
  for macOS ≤ 10.14). Use `yt-dlp_macos` on modern macOS.
- **Gatekeeper quarantine** on the downloaded binary → `xattr -d com.apple.quarantine ~/.local/bin/yt-dlp` if macOS refuses to run it.
- **Stale extractor after a YouTube change** → just run `yt-dlp -U`; 90% of "it stopped
  working" is a one-week-old yt-dlp.
- **pip install of yt-dlp** — don't. It's dead on this Mac (Python 3.9 + YouTube blocks).
  The standalone binary is the only supported path here.
