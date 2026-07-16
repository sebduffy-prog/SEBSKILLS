---
name: blender-mcp-asset-import
category: 3d
description: >-
  Pull real and AI-generated assets into a live Blender session over ahujasid/blender-mcp — Poly Haven
  HDRIs / PBR textures / models, Sketchfab downloads, and text/image-to-3D via Hyper3D Rodin or Hunyuan3D —
  then rescale and place them so they sit correctly in the scene. Use when a scene needs a real HDRI sky,
  a PBR floor/wall material, a downloaded prop, or a generated model. Covers enabling each provider, the
  exact status→search→download→import tool sequence, async job polling for AI generation, and the
  normalize-then-scale step every imported asset needs.
when_to_use:
  - Lighting a scene with a real HDRI environment or dropping in a PBR material from Poly Haven
  - Downloading a specific prop or model from Poly Haven or Sketchfab into the current scene
  - Generating a bespoke 3D model from a text prompt or reference image (Rodin / Hunyuan3D) and importing it
  - Applying an already-downloaded Poly Haven texture to an existing object with set_texture
  - Fixing a just-imported asset that landed at the wrong scale, origin, or position
when_not_to_use:
  - The blender tools are missing / disconnected — run blender-mcp-setup first (the socket must be green)
  - Building geometry by hand from primitives and modifiers — use blender-mcp-scene-building
  - Only checking what is already in the scene (no import) — use blender-mcp-scene-inspection
  - Generating repeatable parametric/scatter geometry in-Blender — use blender-mcp-procedural-generation
  - A render looks wrong and you are diagnosing lighting/materials — use blender-mcp-render-review-loop
keywords:
  - blender
  - blender-mcp
  - polyhaven
  - hdri
  - pbr
  - texture
  - sketchfab
  - hyper3d
  - rodin
  - hunyuan3d
  - text-to-3d
  - image-to-3d
  - asset-import
  - set-texture
  - 3d
similar_to:
  - blender-mcp-setup
  - blender-mcp-scene-building
  - blender-mcp-scene-inspection
  - blender-mcp-render-review-loop
  - blender-mcp-procedural-generation
  - blender-mcp-bpy-api-navigator
inputs_needed: A live blender-mcp connection (setup green); the provider(s) enabled in the N-panel BlenderMCP tab; API keys for Sketchfab/Hyper3D/Hunyuan3D where required; a target size in metres for downloaded/generated models
produces: Real or AI-generated assets imported into the current Blender scene — HDRI world lighting, PBR materials, or meshes — correctly rescaled and placed
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Blender MCP Asset Import

Bring external assets into a live Blender scene through the [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)
providers: **Poly Haven** (HDRIs, PBR textures, CC0 models), **Sketchfab** (downloadable models), and
AI text/image-to-3D via **Hyper3D Rodin** and **Hunyuan3D**. Each provider is a separate opt-in with its
own status tool — always check status first, because a disabled provider returns an error, not a fallback.

## When to use

Reach for this when the scene needs something you should not model by hand: a real-world HDRI for lighting,
a tileable PBR material, a downloaded prop, or a one-off generated model. If you are hand-building geometry,
inspecting, or debugging a render instead, use the sibling skill named in *when_not_to_use*.

## Prerequisites

- **A green blender-mcp connection.** All tools below proxy through the port-9876 socket. If calls error
  with connection refused, stop and run `blender-mcp-setup`.
- **Providers enabled in Blender.** Press **N** over the 3D viewport → **BlenderMCP** tab → tick the
  provider checkbox(es): *Poly Haven*, *Sketchfab*, *Hyper3D*, *Hunyuan3D*. Enabling is per-session UI.
- **API keys where required** (set in `Edit > Preferences > Add-ons > Blender MCP`, or via env vars the
  server reads: `BLENDERMCP_SKETCHFAB_API_KEY`, `BLENDERMCP_HYPER3D_API_KEY`):
  - **Poly Haven** — no key (open CC0 API).
  - **Sketchfab** — free account + API token; only *downloadable* models are accessible.
  - **Hyper3D Rodin** — key, in mode **MAIN_SITE** (hyper3d.ai) or **FAL_AI** (fal.ai). The add-on ships a
    shared **free_trial** key that is rate-limited per day.
  - **Hunyuan3D** — key configured in add-on preferences.
- **Network egress** to each provider's API.
- **The ahujasid/blender-mcp server specifically** — the provider tools in this skill are ahujasid-only;
  if the connected server instead exposes summary-style tools (`get_objects_summary`,
  `get_blendfile_summary_*`), it is a different blender MCP server without these providers (see the
  *Server identity* note in `blender-mcp-setup`).

> The tool names below are the blender-mcp server's own tools (e.g. `get_polyhaven_status`,
> `download_polyhaven_asset`). Under your MCP client they may appear namespaced (`mcp__blender__…`).

## Recipes

### 0. Gate every recipe on the status tool

Call the matching status tool once and read the result before searching. Never assume a provider is on.

```
get_polyhaven_status      → "PolyHaven integration is enabled" (else: enable the checkbox)
get_sketchfab_status
get_hyper3d_status        → also tells you MAIN_SITE vs FAL_AI mode (this drives which params you pass)
get_hunyuan3d_status
```

### 1. Poly Haven — HDRI world lighting

HDRIs are set as the **world environment** automatically on download; there is nothing to place.

```
# optional: see what category tags exist for filtering
get_polyhaven_categories(asset_type="hdris")

search_polyhaven_assets(asset_type="hdris", categories="outdoor,skies")
#   → list of "<name> (ID: <asset_id>)" sorted by download count. Pick an asset_id.

download_polyhaven_asset(asset_id="kloofendal_48d_partly_cloudy",
                         asset_type="hdris", resolution="4k", file_format="hdr")
#   → HDRI installed as world environment. Scene lighting changes immediately.
```

Resolutions: `1k` / `2k` / `4k` / `8k` (higher = slower download + more VRAM). Prefer `2k`–`4k` for lighting.

### 2. Poly Haven — PBR material on an object

Download builds a material from the map set (diffuse/normal/roughness/…). Two paths — download-and-apply,
or download once then apply to many objects with `set_texture`.

```
search_polyhaven_assets(asset_type="textures", categories="floor,wood")

# Path A — download creates a material 'texture_<id>' (not yet on any object):
download_polyhaven_asset(asset_id="wood_floor_deck", asset_type="textures",
                         resolution="2k", file_format="jpg")

# Apply that downloaded texture to a named object (must exist; inspect first):
set_texture(object_name="Floor", texture_id="wood_floor_deck")
#   → returns material name, map list, and node graph so you can confirm it wired up.
```

Texture map projection quality depends on the object's UVs. If the material looks stretched, the mesh needs
a proper UV unwrap (do that in a scene-building step) — `set_texture` does not unwrap for you.

### 3. Poly Haven — CC0 model

```
search_polyhaven_assets(asset_type="models", categories="furniture")
download_polyhaven_asset(asset_id="dining_chair_01", asset_type="models",
                         resolution="2k", file_format="gltf")
#   → mesh imported into the current scene at its native scale. Then rescale/place (see §6).
```

### 4. Sketchfab — download a specific model

`target_size` is **REQUIRED**: the largest dimension in Blender units (metres). This is the whole point —
Sketchfab models arrive at wildly inconsistent scales, so you normalise on import.

```
search_sketchfab_models(query="wooden barrel", downloadable=True, count=20)
#   → each result has a uid. Optionally preview before committing to a download:
get_sketchfab_model_preview(uid="a1b2c3d4e5f6")

download_sketchfab_model(uid="a1b2c3d4e5f6", target_size=1.0)   # barrel ~1 m tall
#   → returns imported object names + final dimensions + bounding box.
```

Only `downloadable=True` results can be fetched, and the model's licence must permit download — respect it.

### 5. AI generation — Hyper3D Rodin (async, poll then import)

Three steps: **generate** (returns job handles) → **poll until finished** → **import**. The generated mesh
is size-normalised, so expect to rescale afterwards. Which parameter you pass depends on the mode from
`get_hyper3d_status`.

```
# 5a. Kick off a job. Text prompt must be English. bbox_condition is an optional
#     [Length, Width, Height] ratio (not absolute size) — e.g. a tall thin lamp:
generate_hyper3d_model_via_text(text_prompt="a weathered brass desk lamp",
                                bbox_condition=[1, 1, 3])
#   → JSON: {"task_uuid": "...", "subscription_key": "..."}   (MAIN_SITE mode)
#     FAL_AI mode returns a request_id instead.

# 5b. Poll. Pass the handle that matches the mode. Loop until terminal:
poll_rodin_job_status(subscription_key="...")   # MAIN_SITE → status "Done"/"Failed"
# poll_rodin_job_status(request_id="...")        # FAL_AI   → status "COMPLETED"/failed
#   Re-call every few seconds; do NOT import until the status is terminal.

# 5c. Import once done. Name the object; pass the handle matching the mode:
import_generated_asset(name="DeskLamp", task_uuid="...")     # MAIN_SITE
# import_generated_asset(name="DeskLamp", request_id="...")  # FAL_AI
```

Image-to-3D is the same flow via `generate_hyper3d_model_via_images` — pass **`input_image_paths`**
(absolute local paths, as a list) in MAIN_SITE mode, or **`input_image_urls`** in FAL_AI mode. Never both.

### 6. Normalise, scale, and place the imported asset

Poly Haven models keep native scale; Rodin/Hunyuan models are normalised; Sketchfab you sized on import.
Almost always the asset needs positioning and a scale sanity-check. Inspect, then adjust — do not guess.

```python
# execute_blender_code — verify real-world size, then place the newest import.
import bpy
obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else bpy.context.active_object
# world-space dimensions in metres:
print("dims", tuple(round(d, 3) for d in obj.dimensions))
# example: sit it on the floor at the origin and scale a 2.4m-tall import down to 1.0m:
target_h = 1.0
if obj.dimensions.z:
    s = target_h / obj.dimensions.z
    obj.scale = (obj.scale.x * s, obj.scale.y * s, obj.scale.z * s)
bpy.context.view_layer.update()                 # refresh dependency graph before reading matrices
obj.location = (0.0, 0.0, obj.dimensions.z / 2) # drop onto Z=0
print("placed", obj.name, tuple(round(v, 3) for v in obj.location))
```

Prefer the provider's own scaling (`target_size` on Sketchfab, `bbox_condition` ratio on Rodin) over
post-hoc `execute_blender_code` when you can — it is fewer moving parts.

## Verify

- **HDRI:** `get_scene_info` / a viewport screenshot shows the new lighting; the World shader has an
  Environment Texture node. Re-render via `blender-mcp-render-review-loop` if lighting is the goal.
- **Material:** `set_texture` / download return lists the maps and texture nodes — confirm the expected
  maps (diffuse, normal, roughness) are present and connected.
- **Model:** it appears in `get_objects_summary`; `obj.dimensions` reads sensible metres (not 0.001 or 900);
  it sits where you placed it, not buried under the floor or off-camera.
- **AI job:** poll returned a terminal status **before** import; `import_generated_asset*` reported success
  and the named object now exists.

## Pitfalls

- **Provider not enabled.** The single most common failure: status tool says disabled → you must tick the
  checkbox in the N-panel BlenderMCP tab. Enabling the add-on is not enabling the provider.
- **Skipping status → mode mismatch on Rodin.** MAIN_SITE uses `subscription_key`/`task_uuid` and
  `input_image_paths`; FAL_AI uses `request_id` and `input_image_urls`. Pass the wrong pair and the job or
  import errors. `get_hyper3d_status` tells you the mode — read it first.
- **Importing before the job finishes.** `poll_rodin_job_status` / `poll_hunyuan_job_status` are polling
  APIs. Import only on a terminal status ("Done"/"COMPLETED"/"DONE"). Polling too eagerly also burns quota.
- **free_trial key exhausted.** The shared Hyper3D trial key allows only a few models/day. On an
  insufficient-balance error, tell the user to wait for the daily reset or get their own key at hyper3d.ai —
  do not retry in a loop.
- **`target_size` omitted on Sketchfab.** It is required; without it the download fails. Even a rough
  real-world height in metres is fine — you can fine-tune after.
- **`set_texture` on a non-existent or badly-UV'd object.** The object must already exist (inspect first),
  and stretched results mean the mesh needs a UV unwrap — `set_texture` will not create UVs.
- **Reading dimensions before the depsgraph updates.** After scaling/moving, call
  `bpy.context.view_layer.update()` before trusting `obj.dimensions` or world matrices, or you read stale values.
- **Huge resolutions by reflex.** `8k` HDRIs/textures are slow to fetch and heavy on VRAM. Default to
  `2k`–`4k` unless the asset fills the frame at close range.
- **Wrong `bbox_condition` mental model.** It is a **ratio** [L, W, H], not absolute metres. `[1,1,3]` means
  "3× taller than wide", regardless of final size — rescale for real dimensions after import.
