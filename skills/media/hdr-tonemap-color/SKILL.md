---
name: hdr-tonemap-color
category: media
description: >
  Fix washed-out, grey, milky, or over-bright HDR video by correctly tonemapping HDR (BT.2020
  PQ/HLG) down to SDR (BT.709) with ffmpeg zscale+tonemap — the ONLY way that doesn't blow out
  highlights or desaturate the picture. Also tags/converts colour spaces (BT.2020↔709, PQ/HLG→gamma),
  reads HDR metadata with ffprobe, and applies .cube 3D LUT grades in the correct linear/log space.
  Reach for this whenever iPhone/iOS or drone footage looks pale, dull, blown-out, or "wrong colour"
  in a browser/editor, when you must "convert HDR to SDR for web", "tonemap HDR", "fix washed out video",
  or "the colours look faded after export". NOT a general LUT-slapper — it gets the colour science right.
when_to_use:
  - "iPhone / iOS HDR (Dolby Vision / HLG) footage looks washed-out, grey or milky on the web or in an editor"
  - "Convert an HDR clip (BT.2020 PQ or HLG) to SDR BT.709 for web/social without blown highlights"
  - "Colours look faded, dull or over-bright after a plain ffmpeg export or a naive scale"
  - "ffprobe shows bt2020/smpte2084/arib-std-b67 and you need proper SDR delivery"
  - "Re-tag or convert a mislabelled colour space (BT.2020 ↔ BT.709, PQ/HLG ↔ gamma)"
  - "Apply a .cube 3D LUT grade correctly (right transfer/range, no double-gamma)"
  - "Batch-normalise a folder of mixed HDR/SDR clips to consistent Rec.709 SDR"
when_not_to_use:
  - "General joins/crossfade/watermark/GIF or a simple LUT on already-SDR footage → use ffmpeg-cookbook"
  - "Reframe 16:9 → 9:16 with subject tracking → use social-video-reframe"
  - "Bulk codec/bitrate/container transcode with no colour issue → use batch-transcode-encode"
  - "Burn captions/subtitles → use whisper-caption-burn"
  - "ffmpeg not installed / no zscale in your build → run media-toolchain-bootstrap first"
keywords: [hdr, sdr, tonemap, tonemapping, zscale, bt2020, bt709, rec709, rec2020, pq, smpte2084, hlg, arib-std-b67, dolby vision, washed out, faded colour, milky video, iphone hdr, lut3d, cube lut, colorspace, colour space, libplacebo, hable, mobius, reinhard, ffprobe, npl]
similar_to: [ffmpeg-cookbook, batch-transcode-encode, social-video-reframe]
inputs_needed:
  - "Absolute path to the input clip (and desired output path)"
  - "Is it actually HDR? (run the ffprobe check below — decides whether tonemapping is even needed)"
  - "Target: SDR BT.709 for web (default), or just a re-tag / LUT grade?"
  - "If applying a LUT: absolute path to the .cube file"
produces: A single Rec.709 SDR (or correctly-tagged / LUT-graded) video file at a path you specify
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# HDR → SDR Tonemapping & Colour-Space Work

The washed-out look happens when HDR footage (BT.2020 primaries + PQ or HLG transfer) is decoded
and shoved into an SDR container **without tonemapping** — players clamp the wide-gamut, high-nit
signal and you get pale, low-contrast, milky colour. The fix is a proper `zscale → tonemap → zscale`
chain that linearises the signal, compresses the dynamic range with a filmic curve, then re-tags as
Rec.709 SDR. Get the order and the tags right and it looks correct everywhere.

## When to use

An iPhone/drone/mirrorless clip looks fine on the source device but grey/faded/blown once it hits a
browser, Premiere, or a naive `ffmpeg -i in.mp4 out.mp4`. Or ffprobe reports `bt2020`/`smpte2084`
(PQ) / `arib-std-b67` (HLG) and you must deliver SDR. This skill gets the colour science right rather
than eyeballing a curves adjustment.

## Prerequisites (this Mac)

- **ffmpeg with zscale + tonemap.** Check: `ffmpeg -filters | grep -E 'zscale|tonemap'` must list
  both. `zscale` needs the zimg library — most full builds have it. The pip **`imageio-ffmpeg`**
  binary and the one in `_research_bank/bin` are the ones to use here (no brew on this Mac):
  ```bash
  FF=$(python3 -c "import imageio_ffmpeg as f; print(f.get_ffmpeg_exe())")
  FP=$(python3 -c "import imageio_ffmpeg,sys,os; sys.stdout.write(os.path.join(os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()),'ffprobe'))" 2>/dev/null)
  "$FF" -filters | grep -E 'zscale|tonemap|libplacebo'
  ```
  If `zscale` is missing, that build lacks zimg — get a zimg-enabled static build; `libplacebo`
  (below) is the GPU fallback but is rarely in the portable pip binary.
- **ffprobe** may not ship beside the pip binary — `$FP` above points at it when it does. If it's
  missing, use `"$FF" -i input.mov` and read the tags from stderr rather than a separate ffprobe.

## Step 0 — Diagnose: is it actually HDR?

Don't tonemap SDR footage (it'll dull it). Read the colour tags first:

```bash
"$FP" -v error -select_streams v:0 \
  -show_entries stream=color_space,color_transfer,color_primaries,pix_fmt \
  -of default=noprint_wrappers=1 input.mov
```

Interpret:
- `color_transfer=smpte2084` → **HDR10 / PQ**. Tonemap. (`color_primaries=bt2020`, 10-bit `p010`.)
- `color_transfer=arib-std-b67` → **HLG**. Tonemap (HLG variant below).
- `color_transfer=bt709`/`bt470bg`/unset + `bt709` primaries → already **SDR**, do NOT tonemap;
  if it merely looks off it's a tag/LUT issue, not a tonemap one.
- Dolby Vision clips usually carry a PQ base layer — treat as PQ (HDR10) here; the DV RPU dynamic
  metadata is dropped, which is fine for SDR web delivery.

## Recipe 1 — HDR10 (PQ) → SDR BT.709 (the default fix)

The canonical, GPU-free chain. Copy, swap paths, run:

```bash
"$FF" -i input.mov -vf \
"zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,\
tonemap=tonemap=hable:desat=0,\
zscale=t=bt709:m=bt709:r=tv,format=yuv420p" \
-c:v libx264 -crf 18 -preset slow -c:a copy -movflags +faststart output_sdr.mp4
```

Why each stage (do not reorder):
- `zscale=t=linear:npl=100` — linearise PQ; `npl` = nominal peak luminance the tonemapper maps to
  ~white. **100 is the key knob for "washed out":** too high (e.g. 1000) → dark/muddy; too low →
  blown. Start 100; raise toward 200–400 only if the result is too dark.
- `format=gbrpf32le` — 32-bit float linear RGB so tonemapping has headroom (no banding).
- `zscale=p=bt709` — gamut-map BT.2020 primaries down to BT.709 while still linear.
- `tonemap=tonemap=hable:desat=0` — filmic Hable curve compresses highlights; `desat=0` stops the
  bright-desaturation that causes the milky look. Alt curves: `mobius` (protects highlights, punchier),
  `reinhard` (softer), `clip` (hard, don't).
- `zscale=t=bt709:m=bt709:r=tv,format=yuv420p` — re-apply Rec.709 gamma, set the 709 YCbCr matrix,
  TV/limited range, 8-bit 4:2:0 for universal playback.

Tuning if it still looks off: too dark → raise `npl` (200/400) or swap `hable`→`mobius`; too flat →
add a gentle contrast via a LUT (Recipe 4) or `eq=contrast=1.05`.

## Recipe 2 — HLG → SDR BT.709

HLG is scene-referred; linearise via the HLG transfer instead of PQ:

```bash
"$FF" -i input_hlg.mov -vf \
"zscale=t=arib-std-b67:npl=1000,tonemap=tonemap=hable:desat=0,\
zscale=t=bt709:m=bt709:r=tv:p=bt709,format=yuv420p" \
-c:v libx264 -crf 18 -preset slow -c:a copy -movflags +faststart output_sdr.mp4
```

`npl=1000` suits HLG's 1000-nit reference; lower to ~200–300 if highlights clip.

## Recipe 3 — GPU / higher-quality alt: libplacebo (BT.2390)

If your build has `libplacebo` (Vulkan), it gives smoother, better-behaved tonemapping in one filter
and handles PQ **and** HLG automatically:

```bash
"$FF" -i input.mov -vf \
"libplacebo=tonemapping=bt.2390:colorspace=bt709:color_primaries=bt709:color_trc=bt709:format=yuv420p" \
-c:v libx264 -crf 18 -c:a copy -movflags +faststart output_sdr.mp4
```

`bt.2390` is the ITU reference tonemap curve; alternatives: `spline`, `mobius`, `hable`. Use only if
`"$FF" -filters | grep libplacebo` lists it — otherwise stick with Recipe 1.

## Recipe 4 — Apply a .cube 3D LUT correctly

A LUT expects a specific input space. Two common cases:

- **SDR footage, creative LUT** (most .cube grades): apply in the video's own (gamma) space, after any
  tonemap. Order matters — tonemap first, LUT last:
  ```bash
  "$FF" -i output_sdr.mp4 -vf "lut3d=/path/to/grade.cube" -c:v libx264 -crf 18 -c:a copy graded.mp4
  ```
- **HDR→SDR conversion LUT** (a .cube built to eat PQ and emit 709): do NOT tonemap as well — that
  double-processes. Just apply the LUT and re-tag:
  ```bash
  "$FF" -i input.mov -vf "lut3d=/path/to/hdr_to_709.cube,zscale=t=bt709:m=bt709:p=bt709:r=tv,format=yuv420p" \
    -c:v libx264 -crf 18 -c:a copy hdr_lut_sdr.mp4
  ```

Interpolation: add `:interp=tetrahedral` to `lut3d` for smoother results than the default trilinear.

## Recipe 5 — Re-tag only (no pixel change), e.g. mislabelled colour space

When the pixels are fine but the tags are wrong (player misinterprets them). This rewrites metadata
without touching the image:

```bash
"$FF" -i mislabelled.mp4 -c copy \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 fixed_tags.mp4
```

(`-c copy` = stream copy, instant, lossless. Use only when the data really is 709 but tagged 2020.)

## Verify

1. **Tags are now SDR** — should print `bt709`/`bt709`/`bt709`:
   ```bash
   "$FP" -v error -select_streams v:0 \
     -show_entries stream=color_space,color_transfer,color_primaries -of default=nw=1 output_sdr.mp4
   ```
2. **Eyeball a frame** — pull a still and look for restored contrast/saturation, no grey wash, no
   clipped-white highlights:
   ```bash
   "$FF" -i output_sdr.mp4 -vf "select=eq(n\,120)" -vframes 1 check.png
   ```
   Compare `check.png` against a frame from the source. If it's dark → raise `npl`; if highlights are
   crushed white → lower `npl` or switch `hable`→`mobius`.
3. Confirm 8-bit `yuv420p` for web: `pix_fmt=yuv420p` in the ffprobe output above.

## Pitfalls

- **Skipping tonemap entirely** (`ffmpeg -i in.mov out.mp4`) is THE cause of washed-out HDR. There is
  no shortcut — you must linearise → tonemap → re-tag.
- **Wrong `npl`** is the #1 tuning mistake: too high = muddy/dark, too low = blown. Default 100 (PQ) /
  1000 (HLG), then adjust by eye.
- **`desat=0` matters** — omit it and bright areas go pale/milky again.
- **Reordering the chain** breaks it: gamut/primaries map must happen in linear light, before the final
  gamma re-encode. Keep the `format=gbrpf32le` float stage.
- **Double-processing**: don't run a tonemap AND an HDR-conversion LUT — pick one.
- **No zscale in the build** → the whole chain silently won't run; verify with `-filters` first, or use
  the `libplacebo` path.
- **10-bit input**: HDR is usually `p010`; the chain outputs 8-bit `yuv420p` on purpose for web. Keep
  `-pix_fmt yuv420p10le` and drop `format=yuv420p` only if you truly need a 10-bit SDR master.
- **Audio**: `-c:a copy` preserves the track; drop it (or use `-an`) only if you don't need sound.
