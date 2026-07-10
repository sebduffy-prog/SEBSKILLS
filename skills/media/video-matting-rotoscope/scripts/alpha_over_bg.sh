#!/usr/bin/env bash
# Composite an RVM alpha matte (pha.mp4) + foreground (fgr.mp4) over any background,
# or key the green-screen composite (com.mp4) onto a new plate, with ffmpeg.
# RVM's alpha is premultiplied-friendly: com = fgr*pha + bg*(1-pha).
set -euo pipefail

FGR="${1:?fgr.mp4}"; PHA="${2:?pha.mp4}"; BG="${3:?background image or video}"; OUT="${4:?out.mp4}"

# fgr and pha are same size/fps as source; scale bg to match, then maskedmerge.
ffmpeg -y -i "$FGR" -i "$PHA" -i "$BG" -filter_complex "\
 [0:v]split[fg][fgref];\
 [2:v][fgref]scale2ref=w=iw:h=ih[bg][fgref2];\
 [1:v]format=gray[m];\
 [bg][fg][m]maskedmerge[out]" \
 -map '[out]' -map '0:a?' -c:a copy -pix_fmt yuv420p "$OUT"
echo "wrote $OUT"
