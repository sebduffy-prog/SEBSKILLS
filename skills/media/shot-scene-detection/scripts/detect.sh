#!/usr/bin/env bash
# Shot/scene detection with PySceneDetect, wiring the portable imageio-ffmpeg
# binary onto PATH so split-video/save-images work on this Mac (no brew ffmpeg).
#
# Usage: detect.sh INPUT OUTDIR [--split]
#   default: adaptive detector -> CSV shot list + EDL + 1 thumbnail per scene
#   --split: additionally split into one frame-accurate clip per shot
set -euo pipefail

INPUT="${1:?usage: detect.sh INPUT OUTDIR [--split]}"
OUTDIR="${2:?usage: detect.sh INPUT OUTDIR [--split]}"
SPLIT="${3:-}"

[ -f "$INPUT" ] || { echo "no such file: $INPUT" >&2; exit 1; }
mkdir -p "$OUTDIR"

# --- ensure a plain 'ffmpeg' is on PATH (portable imageio-ffmpeg binary) ---
if ! command -v ffmpeg >/dev/null 2>&1; then
  FFBIN="$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null || true)"
  if [ -n "$FFBIN" ] && [ -f "$FFBIN" ]; then
    FFDIR="$(dirname "$FFBIN")"
    ln -sf "$FFBIN" "$FFDIR/ffmpeg"
    export PATH="$FFDIR:$PATH"
  else
    echo "ffmpeg not found and imageio-ffmpeg not installed (pip install imageio-ffmpeg)" >&2
    exit 1
  fi
fi

# scenedetect CLI, or module fallback
if command -v scenedetect >/dev/null 2>&1; then SD=(scenedetect); else SD=(python3 -m scenedetect); fi

CMDS=(list-scenes save-edl save-images -n 1)
[ "$SPLIT" = "--split" ] && CMDS+=(split-video)

"${SD[@]}" -i "$INPUT" -o "$OUTDIR" detect-adaptive -m 15 "${CMDS[@]}"

echo "done -> $OUTDIR"
ls -1 "$OUTDIR"
