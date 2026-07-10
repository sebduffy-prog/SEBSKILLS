---
name: photo-to-3d-asset
category: 3d
description: >-
  Turn a single product/hero photo (or a text prompt) into a clean, textured, game/AR-ready
  3D mesh (GLB) using open image-to-3D models — Hunyuan3D-2 or Microsoft TRELLIS. Generation
  needs a GPU (rented/hosted box or API), NOT this Mac; wrap it behind a config'd endpoint,
  then decimate/retopo + UV/texture-clean via blender-mcp and export a compact GLB for
  AR try-on, 3D OOH, turntable renders, or WebGL product pages. Honest about VRAM + licences.
when_to_use:
  - You have one clean product/hero photo and need a usable 3D GLB, not a render
  - Building AR try-on, a WebGL/model-viewer product page, or 3D OOH from a still
  - You want a turntable/hero mesh from a text prompt with no photogrammetry rig
  - You need a repeatable photo->GLB pipeline wired to a rented GPU or hosted API
  - You must decimate/retopo + clean UVs/textures a raw generated mesh before shipping
when_not_to_use:
  - You expect this M-series Mac to run the model locally — it can't; rent a 16GB+ GPU or use an API
  - You need dimensionally-accurate/metrology 3D — use real photogrammetry (RealityCapture, Meshroom)
  - You only need a 2D cutout or flat render — use image_remove_background + a render tool
  - You already have a mesh and only need scene/lighting/render — use blender-mcp-render-review-loop
  - Multi-photo capture rig available — classic photogrammetry beats single-image generation on fidelity
keywords:
  - photo-to-3d
  - image-to-3d
  - hunyuan3d
  - trellis
  - glb
  - ar-try-on
  - textured-mesh
  - single-image
  - blender-mcp
  - retopology
  - decimate
  - gpu-inference
  - model-viewer
  - product-3d
  - text-to-3d
similar_to:
  - blender-mcp-asset-import
  - blender-mcp-render-review-loop
  - blender-mcp-procedural-generation
inputs_needed: >-
  One clean subject-isolated photo (or a text prompt); a reachable GPU with 16GB+ VRAM
  (rented box, HF endpoint, Replicate, or fal) plus its endpoint URL/API key in env.
produces: >-
  A textured .glb (plus intermediate .obj/.ply and a preview turntable), decimated and
  UV/texture-cleaned, ready for model-viewer / AR / OOH.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Photo -> 3D Asset (GLB)

Single photo (or text prompt) -> textured, cleaned, game/AR-ready **GLB**. Generation is
GPU-only open-weights work; the honest architecture is **generate on a rented/hosted GPU
behind a config'd endpoint, clean locally with blender-mcp**.

## When to use

You have one hero/product still and need an actual mesh you can drop into `<model-viewer>`,
USDZ AR quick-look, a WebGL page, or a 3D OOH turntable — fast, no capture rig. Two engines:

| Engine | Repo | Strength | VRAM | Licence |
|---|---|---|---|---|
| **Hunyuan3D-2** | `Tencent-Hunyuan/Hunyuan3D-2` | Best textures; separate shape+paint stages; ships `api_server.py` | 6GB shape / 16GB shape+texture | Tencent Hunyuan Community (check commercial terms) |
| **TRELLIS** | `microsoft/TRELLIS` | Clean geometry, one-call GLB export, `simplify=` built in | 16GB min (A100/A6000) | MIT core (some submodules restricted) |

## Prerequisites

- **A GPU box you do NOT run on this Mac.** Options: rent (RunPod/Lambda/Vast, Linux + CUDA
  11.8/12.2), a Hugging Face Inference Endpoint, or a hosted API (Replicate/fal that host these).
- Endpoint config in env: `P23D_ENDPOINT`, `P23D_API_KEY` (never hardcode — see security rule).
- Local: **Blender running with the MCP add-on connected** (blender-mcp-setup) for cleanup.
- Background removal: `image_remove_background` (Adobe MCP) or `rembg` on the GPU box.
- `python3` (3.9 here) only for orchestration/glTF validation, not model inference.

## Mechanism / Steps

### 1. Prep the input (local)
A clean alpha-cut subject on transparent background is the single biggest quality lever.
Run `image_remove_background` on the source photo, or on the GPU box use `rembg i in.png cut.png`.
Square-ish, centred, even lighting, no harsh shadow. For text-to-3D, skip to step 2 with a prompt.

### 2. Generate on the GPU (remote) — wrap behind ONE endpoint
Stand the model up **once** on the GPU box, then call it over HTTP so the Mac never needs CUDA.

**Hunyuan3D-2 — start the bundled server on the GPU box:**
```bash
# on the rented Linux GPU, after `pip install -r requirements.txt`
python api_server.py --host 0.0.0.0 --port 8080
```
Its Python inference (what the server wraps) is:
```python
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.texgen   import Hunyuan3DPaintPipeline

shape = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained('tencent/Hunyuan3D-2')
mesh  = shape(image='cut.png')[0]                      # geometry
paint = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2')
mesh  = paint(mesh, image='cut.png')                   # textured
mesh.export('out.glb')
```
Low-VRAM (<16GB) gradio path: `python3 gradio_app.py --model_path tencent/Hunyuan3D-2
--subfolder hunyuan3d-dit-v2-0 --texgen_model_path tencent/Hunyuan3D-2 --low_vram_mode`.

**TRELLIS — one-call export (run on the GPU box or a Replicate/fal wrapper):**
```python
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils     import postprocessing_utils
from PIL import Image

pipe = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
pipe.cuda()
outputs = pipe.run(Image.open("cut.png"), seed=1)      # dict: gaussian / radiance_field / mesh
glb = postprocessing_utils.to_glb(
    outputs['gaussian'][0], outputs['mesh'][0],
    simplify=0.95, texture_size=1024)                  # decimation happens HERE
glb.export("out.glb")
```
TRELLIS needs env `ATTN_BACKEND=flash-attn` (or `xformers`) and `SPCONV_ALGO=native` before import.

**Config, don't hardcode.** From the Mac, treat the box as a black-box endpoint:
```bash
curl -s -H "Authorization: Bearer $P23D_API_KEY" \
     -F image=@cut.png "$P23D_ENDPOINT/generate" -o out.glb
```
Validate secrets exist at startup; fail fast if `$P23D_ENDPOINT` is unset (input-validation rule).

### 3. Clean + retopo locally (blender-mcp)
Raw generated meshes are dense, non-manifold, and over-UV'd. Import `out.glb` into Blender and
run `mcp__blender__execute_blender_code` — inspect first (never assume the object name):
```python
import bpy
bpy.ops.import_scene.gltf(filepath="/abs/path/out.glb")
obj = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = obj
# target polycount for real-time (AR/web): ~20-40k tris
d = obj.modifiers.new("decimate", 'DECIMATE'); d.ratio = 0.3
bpy.ops.object.modifier_apply(modifier=d.name)
bpy.ops.object.shade_smooth()
```
Then: recalc normals (`mesh.normals_make_consistent`), fix scale/origin (set to a real-world
size so AR places it correctly), and if geometry is rough, Smart-UV-Project + bake the generated
texture to a fresh 1–2k atlas. Keep it immutable-friendly: export a NEW file, don't overwrite `out.glb`.

### 4. Export the shippable GLB
```python
bpy.ops.export_scene.gltf(filepath="/abs/path/final.glb",
    export_format='GLB', export_draco_mesh_compression_enable=True,
    export_yup=True)   # Y-up = model-viewer / USDZ convention
```
Draco + a single texture atlas keeps it small for web/AR. For a hero turntable render instead,
hand `final.glb` to **blender-mcp-render-review-loop**.

## Verify

- `python3 -c "from pygltflib import GLTF2; g=GLTF2().load('final.glb'); print(len(g.meshes),'meshes', len(g.materials),'mats')"` — mesh + material present.
- Tri count in target band (~20–40k real-time): check `sum(p.count for p in mesh.polygons)` in Blender.
- Drop into a `<model-viewer ar>` page (or Apple AR Quick Look) — loads, textured, correctly scaled, no missing faces.
- Turntable render (blender-mcp) reads clean from all angles; no inside-out normals / z-fighting.
- File size sane: a web product GLB should land roughly 1–6 MB after Draco + atlas.

## Pitfalls

- **This Mac cannot generate.** No brew/CUDA, python3.9 — do NOT attempt local inference; rent a 16GB+ GPU or use a hosted API. This is the #1 failure.
- **Licences bite commercially.** TRELLIS core is MIT but some submodules are restricted; Hunyuan3D-2 is under Tencent's community licence — read both before any client/OOH use.
- **Garbage in, garbage out.** A busy/low-alpha input gives a blobby mesh; the background cut in step 1 matters more than the engine choice.
- **Single-image ≠ accurate.** The unseen back is hallucinated. Not for metrology or anything dimensionally load-bearing — say so to the client.
- **Raw mesh is un-shippable.** Hundreds of k tris, messy UVs. Skipping step 3 gives a GLB that janks on mobile AR. Always decimate + re-atlas.
- **Wrong up-axis / scale** makes AR place the model sideways or metres tall — set Y-up and a real-world scale on export.
- **Secrets in code.** Endpoint URL/key belong in env, validated at startup; never commit them.
- **Cold start cost.** Model + weights load is slow (minutes) — keep the endpoint warm for batches rather than per-photo spin-up.
