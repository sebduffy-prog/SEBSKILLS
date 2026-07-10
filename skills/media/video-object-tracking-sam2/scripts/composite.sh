#!/usr/bin/env bash
# Composite a SAM 2 mask-PNG sequence onto the source video as an effect.
# Usage: composite.sh SRC MASKDIR EFFECT OUT [--grow N]
#   EFFECT: blur | pixelate | redact | alpha | greenscreen | overlay
#   --grow N  dilate the mask by N px (safety margin for redaction)
# Runs locally; needs ffmpeg on PATH (portable imageio-ffmpeg is fine).
set -euo pipefail

SRC="${1:?source video}"; MASKDIR="${2:?mask dir}"; EFFECT="${3:?effect}"; OUT="${4:?output}"
shift 4
GROW=0
while [ $# -gt 0 ]; do case "$1" in --grow) GROW="$2"; shift 2;; *) shift;; esac; done

command -v ffmpeg >/dev/null || { echo "ffmpeg not on PATH (see SKILL.md Prerequisites)"; exit 1; }

# Match source fps so masks and frames stay in sync over long clips.
FPS=$(ffprobe -v0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate "$SRC")
MASKS="$MASKDIR/%05d.png"

# Build a gray alpha from the mask; optionally dilate for a safety margin.
DIL=""; [ "$GROW" -gt 0 ] && DIL="dilation=coordinates=255:${GROW}, "
MASK_CHAIN="[1:v]format=gray,${DIL}geq=lum='p(X,Y)':a='p(X,Y)'[m]"

case "$EFFECT" in
  blur)
    FC="[0:v]boxblur=20:2[fx];${MASK_CHAIN};[0:v][fx][m]maskedmerge[out]" ;;
  pixelate)
    FC="[0:v]scale=iw/16:ih/16,scale=iw*16:ih*16:flags=neighbor[fx];${MASK_CHAIN};[0:v][fx][m]maskedmerge[out]" ;;
  redact)
    FC="color=c=black:s=1x1,scale=1920:1080[bk];[0:v][bk]scale2ref[v0][blk];${MASK_CHAIN};[v0][blk][m]maskedmerge[out]" ;;
  overlay)
    FC="color=c=red:s=1x1[rc];[0:v][rc]scale2ref[v0][red];${MASK_CHAIN};[v0][red][m]maskedmerge=0.5[mix];[v0][mix]blend=all_mode=normal:all_opacity=1[out]" ;;
  alpha|greenscreen)
    : ;;  # handled below (need alpha channel)
  *) echo "unknown effect: $EFFECT"; exit 1 ;;
esac

if [ "$EFFECT" = "alpha" ]; then
  # Object cut out, background transparent -> ProRes 4444 (.mov keeps alpha).
  ffmpeg -y -i "$SRC" -framerate "$FPS" -i "$MASKS" -filter_complex \
    "[1:v]format=gray[a];[0:v][a]alphamerge[out]" \
    -map '[out]' -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le "$OUT"
elif [ "$EFFECT" = "greenscreen" ]; then
  ffmpeg -y -i "$SRC" -framerate "$FPS" -i "$MASKS" -filter_complex \
    "color=c=0x00FF00:s=1x1[g];[0:v][g]scale2ref[v0][grn];[1:v]format=gray,geq=lum='p(X,Y)':a='p(X,Y)'[m];[grn][v0][m]maskedmerge[out]" \
    -map '[out]' -map 0:a? -c:a copy "$OUT"
else
  ffmpeg -y -i "$SRC" -framerate "$FPS" -i "$MASKS" -filter_complex "$FC" \
    -map '[out]' -map 0:a? -c:a copy "$OUT"
fi

echo "wrote $OUT"
