#!/usr/bin/env bash
# media-toolchain-bootstrap — one-shot macOS setup/repair of the media toolchain.
# Installs into ~/.local/bin (no brew, no sudo): standalone yt-dlp + portable deno,
# and ensures a portable ffmpeg via the imageio-ffmpeg pip wheel.
# Idempotent: re-running upgrades/repairs. Safe to run as a "fix yt-dlp" button.
set -euo pipefail

BIN="${MEDIA_BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN"

log() { printf '\033[1;36m[bootstrap]\033[0m %s\n' "$*"; }

# ---- 1. yt-dlp (standalone macOS binary; pip build is dead on this Mac) --------
log "installing/updating yt-dlp standalone macOS binary -> $BIN/yt-dlp"
curl -fL --retry 3 \
  https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos \
  -o "$BIN/yt-dlp"
chmod +x "$BIN/yt-dlp"

# ---- 2. deno (portable JS runtime; yt-dlp needs it to solve YouTube nsig) ------
if ! command -v deno >/dev/null 2>&1 && [ ! -x "$BIN/deno" ]; then
  log "installing portable deno (required for YouTube n-sig / player challenges)"
  # DENO_INSTALL points the installer at our bin dir; no shell-profile edits.
  export DENO_INSTALL="$HOME/.deno"
  curl -fsSL https://deno.land/install.sh | sh -s -- -y >/dev/null
  ln -sf "$DENO_INSTALL/bin/deno" "$BIN/deno"
else
  log "deno already present — skipping"
fi

# ---- 3. ffmpeg via imageio-ffmpeg (portable wheel; no brew on this Mac) --------
log "ensuring imageio-ffmpeg (portable ffmpeg binary)"
python3 -m pip install --quiet --user --upgrade imageio-ffmpeg >/dev/null 2>&1 || \
  python3 -m pip install --quiet --break-system-packages --upgrade imageio-ffmpeg
FFMPEG="$(python3 -c 'import imageio_ffmpeg as f; print(f.get_ffmpeg_exe())')"
ln -sf "$FFMPEG" "$BIN/ffmpeg"

# ---- 4. report -----------------------------------------------------------------
log "done. Ensure PATH contains: $BIN"
echo "  export PATH=\"$BIN:\$PATH\""
echo
"$BIN/yt-dlp" --version   | sed 's/^/yt-dlp   /'
"$BIN/deno"   --version   | head -1 | sed 's/^/deno     /'
"$BIN/ffmpeg" -version    | head -1 | sed 's/^/ffmpeg   /'
