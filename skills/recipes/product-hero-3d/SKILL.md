---
name: product-hero-3d
category: recipes
description: >-
  Recreate a Hunyuan3D-2 / TRELLIS style image-to-3D asset pipeline as a named combo: turn one
  clean product photo into a textured 3D mesh and a polished orbiting turntable MP4. Chain
  background-removal-batch to isolate the product, photo-to-3d-asset to generate the GLB mesh (the
  one GPU/API step), blender-mcp-scene-building + blender-mcp-render-review-loop to light, stage and
  look-dev a hero shot, then ffmpeg-cookbook to stitch the orbit frames into a delivery turntable.
  Reach for this for a 3D product hero, AR/WebGL asset, or spinning turntable from a single still.
when_to_use:
  - You have one clean product/hero photo and want both a 3D mesh AND a finished turntable video
  - Recreating a Hunyuan3D-2 / TRELLIS image-to-3D "asset + spin" demo end-to-end from a still
  - Building a 3D product hero for a landing page, OOH, or pitch without a photogrammetry rig
  - You need a repeatable still->GLB->lit-render->turntable pipeline, not a one-off render
  - You want the generated mesh cleaned, staged and lit properly before it ships, not raw output
when_not_to_use:
  - You only need a flat transparent cutout of the product — use background-removal-batch alone
  - You only need the raw GLB mesh with no staging or video — use photo-to-3d-asset alone
  - You already have a mesh and only need lighting/framing/render — use blender-mcp-render-review-loop alone
  - You only need to encode/stitch existing frames into a video — use ffmpeg-cookbook alone
  - You need dimensionally-accurate metrology 3D — use real photogrammetry, not single-image generation
keywords:
  - hunyuan3d
  - trellis
  - image-to-3d
  - photo-to-3d
  - product hero
  - turntable
  - 3d asset
  - glb
  - blender
  - background removal
  - look-dev
  - render loop
  - ffmpeg
  - orbit render
  - webgl product
  - ar asset
  - combo
  - recipe
similar_to:
  - background-removal-batch
  - photo-to-3d-asset
  - blender-mcp-scene-building
  - blender-mcp-render-review-loop
  - ffmpeg-cookbook
inputs_needed: >-
  One clean, well-lit product/hero photo (single dominant subject, ideally isolable). Access to a
  GPU box or hosted image-to-3D API (Hunyuan3D-2 or TRELLIS) for the mesh step — this Mac cannot run
  it locally. A live Blender + MCP session (blender-mcp-setup) for staging/render, and ffmpeg on PATH
  for the turntable encode. A scratch working dir for the cutout, GLB, orbit frames and output MP4.
produces: >-
  A textured 3D mesh (GLB) of the product, a set of lit orbit frames rendered around it in Blender,
  and a delivery turntable MP4 (optional GIF + poster frame) — a reproducible still-to-spin asset
  package suitable for a WebGL/model-viewer page, AR try-on, or a product hero.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Product Hero 3D

Recreate the headline trick of Tencent's **Hunyuan3D-2** and Microsoft's **TRELLIS** demos —
"drop in one product photo, get back a rotating 3D asset" — by chaining skills that already exist
in this library. One still goes in; a clean textured mesh and a polished orbiting turntable come out,
with the generated geometry properly lit and staged instead of shown as raw model-viewer output.

## What it recreates

The **image-to-3D asset + turntable** experience popularised by **Hunyuan3D-2** and **Microsoft
TRELLIS** (and the hosted "photo → spinnable 3D" tools built on them). Those demos take a single
image and return a textured mesh you can orbit. This recipe reproduces the same user-facing result
— photo in, mesh + spin out — but the "spin" here is a real Blender render pass rather than a raw
WebGL model-viewer, so lighting and framing are art-directed.

## Feasibility

**Rating: amber.** Fully reproducible EXCEPT for one step. The mesh-generation step
(**photo-to-3d-asset**) runs Hunyuan3D-2 / TRELLIS, which needs a **16GB+ GPU or a hosted API** — it
will NOT run on this M-series Mac. That is the amber step, and the honest one to flag up front.

Everything on either side of it is local and green: **background-removal-batch** runs locally via
rembg, and the staging, look-dev render loop and turntable encode all run on this machine through
the connected Blender MCP session and ffmpeg. So the pipeline is local end-to-end apart from the
single rented-GPU / API call for the mesh.

Do not oversell fidelity: single-image generation guesses the unseen back of the object and can
produce soft or lumpy geometry. This recreates a *convincing hero asset*, not a metrology-accurate
scan. If dimensional accuracy matters, use real photogrammetry instead — the recipe cannot fix that.

## The combo

An ordered chain. Each step names the exact sibling skill.

1. **background-removal-batch** — isolate the product to a clean transparent PNG (real alpha) with
   rembg. A tight cutout on a neutral field gives the image-to-3D model the best possible silhouette
   and stops the background bleeding into the generated mesh. Local, no key.
2. **photo-to-3d-asset** — the amber step. Feed the cutout to Hunyuan3D-2 or TRELLIS on a GPU/API to
   generate a textured mesh, then decimate/retopo and clean UVs/textures and export a compact GLB.
   This is the only step that leaves this Mac (rented GPU or hosted endpoint).
3. **blender-mcp-scene-building** — import the GLB into the live Blender session and build the stage:
   ground plane, a three-point or studio light rig, a hero camera, and a Principled-BSDF touch-up if
   the imported material needs it. Additive, non-destructive bpy over MCP.
4. **blender-mcp-render-review-loop** — look-dev the shot: render, Read the image back, critique what
   is actually on screen, adjust ONE of camera / lighting / material, re-render until the hero frame
   matches intent. Then drive the camera (or object) through a full 360° orbit, rendering the frame
   sequence for the turntable.
5. **ffmpeg-cookbook** — stitch the rendered orbit frames into a smooth looping turntable MP4 at the
   target resolution/fps, and optionally emit a GIF and a poster frame. Exact commands, not guidance.

## Prerequisites

- A clean single-subject product photo, and a scratch working dir for cutout / GLB / frames / MP4.
- A GPU box or hosted Hunyuan3D-2 / TRELLIS endpoint reachable for **photo-to-3d-asset** (the amber
  step). Confirm VRAM (16GB+) and check the model licence before commercial use.
- A running **Blender + MCP** session (see `blender-mcp-setup`) so the `mcp__blender__*` tools work.
- **ffmpeg** on PATH (imageio-ffmpeg or the portable binary both work on this Mac — see memory note).
- rembg available for **background-removal-batch** (installed on first run; fully local).

## Run it

1. **Cut out the product.** Invoke **background-removal-batch** on the source photo to get a
   transparent PNG. Square-pad it if the model wants a consistent frame. Eyeball the alpha edge —
   stray background pixels become geometry noise downstream.
2. **Generate the mesh (amber).** Invoke **photo-to-3d-asset**: send the cutout to the Hunyuan3D-2 /
   TRELLIS endpoint, then run its decimate/retopo + UV/texture-clean and export a compact **GLB**.
   This is the one step off this machine; everything after is local.
3. **Stage it in Blender.** Invoke **blender-mcp-scene-building**: import the GLB, add a ground plane,
   set up a studio / three-point light rig, place a hero camera framing the product, and touch up the
   Principled-BSDF material if the import looks flat. Inspect the scene first; mutate additively.
4. **Look-dev the hero frame.** Invoke **blender-mcp-render-review-loop**: render, Read the image,
   critique it, change ONE variable, re-render — until the still is the shot you want (framing,
   key/fill balance, material read). Do not sign off on pixels you have not looked at.
5. **Render the orbit.** Still in the render loop, animate a 360° orbit — rotate the camera around the
   product (or spin the object on a turntable) — and render the frame sequence to numbered PNGs
   (e.g. `frame_%04d.png`) at your target fps. Keep lighting fixed so only the object appears to spin.
6. **Encode the turntable.** Invoke **ffmpeg-cookbook**: stitch the frames
   (`-framerate N -i frame_%04d.png … -pix_fmt yuv420p`) into a looping H.264 MP4 at the target
   resolution; optionally emit a clean GIF (palettegen/paletteuse) and grab a poster PNG.

## Verify

- Open the GLB in a model-viewer and confirm the mesh is watertight-ish, textured, and the unseen
  back is plausible — flag softness rather than pretending it is a scan.
- Confirm the turntable loops seamlessly (last frame meets first) and the object rotation is even —
  no speed ramp or stutter from dropped frames. `ffprobe` the MP4 for duration/fps/resolution.
- Check the lighting stays fixed across the orbit (only the product spins); a wobbling key light is
  the classic tell that the light rig got parented to the camera by mistake.
- Confirm resolution and aspect match the brief, and that colours in the MP4 match the Blender render
  (WebGL/preview vs H.264 can shift gamma — eyeball, don't assume).
- Sanity-check scale/framing: the product should sit consistently in frame through the whole rotation.

## Pitfalls

- **Overselling fidelity (the amber trap).** Single-image generation invents the hidden geometry.
  Present it as a hero asset, not a measured scan; if accuracy matters, say so and switch to
  photogrammetry. This is the honest boundary of the whole recipe.
- **Assuming the mesh step runs locally.** It does not on this Mac — it needs a 16GB+ GPU or a hosted
  API. Wire that endpoint before starting or the pipeline stalls at step 2.
- **Dirty cutout → lumpy mesh.** Background fringing or a cut-off subject in step 1 propagates into
  the generated geometry. Get a clean, complete silhouette before generating.
- **Raw import shipped as-is.** The generated GLB often has dense geometry, odd UVs, or a flat
  material. Skipping the Blender staging/look-dev (steps 3–4) is what makes these look like AI slop —
  the cleanup is the point, not optional polish.
- **Light rig parented to the orbit camera.** If lights ride with the camera, the product's shading
  never changes and the spin looks fake/dead. Keep the rig on a fixed world axis; orbit only the
  camera, or spin only the object.
- **Frame count vs loop length.** Too few orbit frames judders; a 360° that doesn't divide evenly by
  your frame count won't loop cleanly. Pick a frame count that closes the loop exactly.
- **ffmpeg gamma/pixel-format shift.** Encode with explicit `-pix_fmt yuv420p` and check the palette
  against the Blender frames rather than trusting defaults.
