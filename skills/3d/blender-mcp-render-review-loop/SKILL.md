---
name: blender-mcp-render-review-loop
category: 3d
description: >-
  Close the visual feedback loop in a live Blender + MCP session: render (or screenshot the
  viewport), Read the resulting image back, critique what is ACTUALLY on screen, then change
  ONE of camera / lighting / material and re-render until the frame matches intent. Use whenever
  a render looks wrong, a shot needs framing, lighting is flat or blown out, or you are doing
  look-dev iteration — never sign off on pixels you have not looked at.
when_to_use:
  - A render or scene "looks off" and you need to see it before adjusting camera, lights, or materials
  - Framing / composing a hero shot through the scene camera
  - Look-dev iteration — dialling exposure, key/fill/rim lighting, shadows, or material response
  - Sanity-checking a scene you just built (blender-mcp-scene-building) before final render
  - Any time you are about to claim a render is "done" without having read the image back
when_not_to_use:
  - The mcp__blender__* tools error with connection refused — fix the socket first via blender-mcp-setup
  - You only need object counts / transforms / hierarchy as data, not pixels — use blender-mcp-scene-inspection
  - Adding or transforming geometry and objects — use blender-mcp-scene-building
  - Importing PolyHaven / Sketchfab / Hyper3D assets — use blender-mcp-asset-import
  - Looking up a bpy operator or property signature — use blender-mcp-bpy-api-navigator
keywords:
  - blender
  - mcp
  - render
  - viewport
  - screenshot
  - look-dev
  - lighting
  - camera
  - composition
  - feedback-loop
  - eevee
  - cycles
  - thumbnail
  - iterate
  - review
  - 3d
similar_to:
  - blender-mcp-setup
  - blender-mcp-scene-building
  - blender-mcp-scene-inspection
  - blender-mcp-asset-import
  - blender-mcp-procedural-generation
  - blender-mcp-bpy-api-navigator
inputs_needed: A live blender-mcp connection (see blender-mcp-setup); a scene with at least one camera and one light; a filesystem path Claude can Read on the machine running Blender (for render_* tools) OR a visible VIEW_3D area (for the screenshot tools)
produces: A converged frame, images Read back inline on each pass, and a short critique-and-adjust log recording which single change fixed what
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Blender MCP Render / Review Loop

You cannot fix what you have not seen. This skill is the disciplined loop of **render → look → critique →
change one thing → re-render** against a live [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)
session. The failure mode it prevents: emitting bpy that "should" light the scene, never reading a pixel,
and declaring victory on a black or blown-out frame.

## When to use

Reach for this the moment the goal is *how the frame looks* rather than *what is in the scene*. It sits
downstream of `blender-mcp-scene-building` (geometry exists) and `blender-mcp-scene-inspection` (you know
the object graph) — here you judge and tune the *image*.

## Prerequisites

- A green blender-mcp round-trip (`blender-mcp-setup`). Every tool below fails with a socket error otherwise.
- A **scene camera**: `bpy.context.scene.camera` must be set, or `render_*` produces nothing useful.
- At least one light, unless the world/emission is doing the lighting.
- For `render_*`: a filesystem path **on the machine running Blender** that Claude can `Read` back. If
  Blender is remote, the written PNG is not on your disk — use the screenshot tools, or base64 it back
  (see Pitfalls).
- For the screenshot tools: a real, visible **VIEW_3D** area. Headless / background Blender has none.

## Two ways to get pixels — pick deliberately

| Tool | Returns | Shows | Speed | Use for |
|---|---|---|---|---|
| `get_screenshot_of_area_as_image` (`area_ui_type:"VIEW_3D"`) | image **inline** | current viewport shading | instant | framing, quick composition checks |
| `get_screenshot_of_window_as_image` | image **inline** | whole Blender UI | instant | debugging UI/panel state, not the shot |
| `render_thumbnail_to_path` | writes small PNG to path | the **real render** (low quality) | fast | fast look-dev passes |
| `render_viewport_to_path` | writes PNG to path at current render settings | the **real render** (full) | slow | the final frame |

Key distinction: **screenshot tools hand you the image directly**; **render_* only writes a file** — you must
then `Read` that path to actually see it. A viewport screenshot in *Solid* shading shows none of your
materials or lighting; set the viewport to *Rendered* first (below) if you want it to be representative.

## The loop

### 1. State the intent explicitly (one sentence)
"Warm key from screen-left, subject centred on the lower third, no clipped highlights." Without a target you
cannot critique — you can only vibe.

### 2. Make the viewport representative, then get a baseline
Set rendered shading so a fast screenshot actually resembles the render:

```python
# execute_blender_code — flip the active VIEW_3D to Rendered shading
import bpy
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces.active.shading.type = 'RENDERED'
result = {"shading": "RENDERED"}
```

Then either screenshot the VIEW_3D area (inline, fast) **or** drop a thumbnail and Read it:

```
render_thumbnail_to_path(output_path="/tmp/blender_review/iter_01.png")
```
Then `Read` `/tmp/blender_review/iter_01.png`.

### 3. Critique what is on screen — concretely
Score the frame against the intent on named axes, not "looks nice":
- **Exposure** — crushed blacks? blown highlights? Check the bright/dark extremes.
- **Framing** — subject placement, headroom, is anything clipped at the frame edge or camera near-plane?
- **Composition** — leading lines, balance, empty quadrants.
- **Lighting shape** — is there a key/fill/rim read, or is it flat and shadowless?
- **Material** — does metal read as metal, glass as glass, or is everything matte plastic?

### 4. Change exactly ONE thing
Isolate cause and effect. Camera example — aim it at a target and frame the selection:

```python
import bpy, mathutils
cam = bpy.context.scene.camera
target = bpy.data.objects["Suzanne"]          # inspect first; do not assume names
direction = target.location - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
bpy.context.view_layer.update()
result = {"aimed_at": target.name}
```

Lighting example — nudge the key energy and colour temperature:

```python
import bpy
key = bpy.data.objects["Key"].data           # a Light datablock
key.energy = 800                             # watts (Eevee/Cycles)
key.color = (1.0, 0.85, 0.7)                 # warm
result = {"energy": key.energy}
```

Render-engine / sampling for the final pass (fast Eevee for iteration, Cycles for the money shot):

```python
import bpy
sc = bpy.context.scene
# EEVEE's engine id changed across versions: legacy 'BLENDER_EEVEE' (<4.2),
# 'BLENDER_EEVEE_NEXT' (4.2–4.x), then renamed back to 'BLENDER_EEVEE' (5.0+).
# Setting the wrong id raises an enum error, so pick defensively by version.
eevee = 'BLENDER_EEVEE_NEXT' if (4, 2) <= bpy.app.version < (5, 0) else 'BLENDER_EEVEE'
sc.render.engine = eevee                     # or 'CYCLES'
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.film_transparent = False
result = {"engine": sc.render.engine}
```

### 5. Re-render to a NEW filename, Read, compare, repeat
Write `iter_02.png`, `iter_03.png`, … — never overwrite the same path (see Pitfalls). Read each, compare to
the previous, and log the single change and its effect. Stop when the frame meets the intent or the last two
passes are indistinguishable.

## Verify

The loop is working when you can, from a Read-back image, describe the frame in the critique axes above and
name what your last change did to it. Quick smoke test:

```
render_thumbnail_to_path(output_path="/tmp/blender_review/smoke.png")
```
Then `Read` it. If you see the scene and can state its exposure and framing, you are in the loop. If the file
is missing, Blender is remote or the path is unwritable → use `get_screenshot_of_area_as_image` instead.

## Pitfalls

- **`render_*` writes a file; it does not return the image.** You have not "seen" it until you `Read` the
  path. Screenshot tools return inline — no Read needed.
- **Remote Blender → the PNG is not on your disk.** Read fails. Either use the inline screenshot tools, or
  base64 the file back through code: read the bytes in `execute_blender_code`, assign
  `result = {"b64": base64.b64encode(open(path,'rb').read()).decode()}`, and decode locally.
- **Reusing the same output path caches stale pixels.** The Read tool can hand back the previous image.
  Always increment the filename (`iter_NN.png`).
- **Solid-shaded viewport screenshot lies.** It shows no materials or scene lights — set
  `shading.type = 'RENDERED'` first, or use a real render, before judging lighting/material.
- **No scene camera → empty/garbage render.** Confirm `bpy.context.scene.camera` is set before `render_*`.
- **Screenshots need a visible VIEW_3D area.** Background/headless Blender has none — the screenshot tools
  error; fall back to `render_*`.
- **Changing five things per pass.** You will not know which one helped. One variable at a time is the
  entire point of the loop.
- **Cycles at low samples is slow and noisy.** Iterate in Eevee; switch to Cycles only for the final frame.
- **Never assume object/light names.** Inspect the scene (blender-mcp-scene-inspection) and honour existing
  names — the server's own guidance is "NEVER assume missing values".
