---
name: blender-mcp-scene-building
category: 3d
description: >
  Build and modify a Blender scene over MCP with CORRECT bpy — add primitives, set
  transforms/parenting, author Principled-BSDF materials, place lights and cameras, and
  fire a render — choosing operators (`bpy.ops`) vs the data API (`bpy.data`) deliberately
  and never clobbering the existing scene. Reach for this when someone says "add a cube /
  sphere in Blender", "make it red / metallic / emissive", "set up a three-point light",
  "point the camera at the object", "move/rotate/scale that mesh", or "render the scene"
  through the connected `mcp__blender__*` tools. Inspect state FIRST, mutate additively,
  update the depsgraph before reading computed values.
when_to_use:
  - "Adding new objects (mesh primitives, empties, text) to a live Blender scene via MCP"
  - "Transforming existing objects: setting location/rotation/scale, parenting, or applying transforms"
  - "Authoring or assigning materials — base colour, metallic, roughness, emission — with shader nodes"
  - "Placing and aiming lights (sun/point/area) and cameras, including track-to constraints"
  - "Triggering a render or viewport capture after building, and iterating on the look"
  - "Any 'create/modify then render' loop where getting operator-vs-data-API and mode right matters"
when_not_to_use:
  - "The MCP server isn't connected or the add-on is off → blender-mcp-setup first"
  - "You only need to READ scene contents (list objects, dump a datablock) → blender-mcp-scene-inspection"
  - "Rendering + visually critiquing + re-rendering as a tight feedback loop → blender-mcp-render-review-loop"
  - "Importing external .blend/glTF/obj assets or downloading models → blender-mcp-asset-import"
  - "Looking up an unfamiliar bpy class/operator signature → blender-mcp-bpy-api-navigator"
keywords: [blender mcp, bpy, execute_blender_code, bpy.ops, bpy.data, principled bsdf, material nodes, add primitive, transform object, parenting, sun light, area light, camera, track_to constraint, depsgraph, render, scene building, mesh primitive]
similar_to: [blender-mcp-setup, blender-mcp-scene-inspection, blender-mcp-render-review-loop, blender-mcp-asset-import, blender-mcp-procedural-generation, blender-mcp-bpy-api-navigator]
inputs_needed:
  - "A running Blender with the MCP add-on connected (mcp__blender__* tools available)"
  - "What to build: object types, target look (colour/material), lighting intent, camera framing"
  - "Whether to add to the current scene or start from a known state (ask before clearing anything)"
produces: New/modified objects, materials, lights, and cameras in the live Blender scene, optionally a rendered image file
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Build a Blender Scene over MCP with Correct bpy

## When to use

You are connected to a Blender instance through the `mcp__blender__*` tools and need to
**create or change** scene content — objects, materials, lights, cameras — then optionally
render. This skill is about doing the mutation *correctly*: right API for the job, right
mode/selection, no accidental destruction of existing work.

## Prerequisites

- Blender running with the MCP add-on enabled and **connected**. If tool calls error with
  "not connected", stop and run `blender-mcp-setup`.
- Deferred tools loaded. Batch them in one call:
  `ToolSearch "select:mcp__blender__get_objects_summary,mcp__blender__get_object_detail_summary,mcp__blender__execute_blender_code,mcp__blender__render_viewport_to_path,mcp__blender__search_api_docs"`
- Grounded on Blender **4.x** bpy. Socket names below (`Base Color`, `Emission Color`,
  `Emission Strength`) are the 4.x names — 3.x used `Emission`. If unsure of a version-
  specific name, `search_api_docs` before guessing.

## The two rules that prevent most breakage

1. **Inspect before you mutate.** Never assume the scene is empty or that a name is free.
   Call `get_objects_summary` first; if a name collides, Blender silently appends `.001`
   and your later lookups miss.
2. **Operators vs data API — pick deliberately:**
   - `bpy.ops.*` = user-facing actions with sane defaults & context (add primitive, apply
     modifier, set origin). They **depend on mode + active/selected object** and mutate
     selection as a side effect.
   - `bpy.data.*` = precise, context-free datablock control (create a material, set
     `obj.location`, link into a collection). Prefer it for scripted, side-effect-free work.

## Recipe 1 — Inspect, then add a primitive

Always look first.

```
# mcp__blender__get_objects_summary  → names, types, transforms already present
```

Add via operator (gets defaults + is placed at the 3D cursor — reset it for determinism):

```python
import bpy
bpy.context.scene.cursor.location = (0, 0, 0)          # don't inherit a stray cursor
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 1))
obj = bpy.context.active_object                         # operator sets active
obj.name = "HeroSphere"                                 # name explicitly, check no clash
bpy.ops.object.shade_smooth()                           # acts on selection the op just set
```

Data-API alternative when you want zero context dependence (e.g. instancing shared mesh):

```python
import bpy
mesh = bpy.data.meshes.new("PlaneMesh")                 # empty mesh; fill via bmesh if needed
obj  = bpy.data.objects.new("GroundRef", mesh)
bpy.context.collection.objects.link(obj)                # nothing exists until it's linked
```

## Recipe 2 — Transform, parent, apply

Set transforms directly on the datablock — no operator, no selection dance:

```python
import bpy
obj = bpy.data.objects["HeroSphere"]
obj.location       = (0.0, 0.0, 1.0)
obj.rotation_euler = (0.0, 0.0, 0.7854)                 # radians (45°); use math.radians()
obj.scale          = (1.0, 1.0, 1.0)
```

Parent without moving the child in world space:

```python
child, parent = bpy.data.objects["HeroSphere"], bpy.data.objects["Rig"]
child.parent = parent
child.matrix_parent_inverse = parent.matrix_world.inverted()   # keeps visual position
```

Applying transforms (bake into mesh) **needs** the operator + correct selection:

```python
import bpy
bpy.ops.object.select_all(action='DESELECT')
obj = bpy.data.objects["HeroSphere"]
obj.select_set(True)
bpy.context.view_layer.objects.active = obj             # active AND selected required
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
```

If you read a world matrix right after moving something, **update the depsgraph first**,
or you get the stale value:

```python
bpy.context.view_layer.update()
print(bpy.data.objects["HeroSphere"].matrix_world.translation)
```

## Recipe 3 — Author a Principled BSDF material (data API)

```python
import bpy
mat = bpy.data.materials.get("HeroMat") or bpy.data.materials.new("HeroMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")       # default node in a new node tree
bsdf.inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1.0)   # RGBA, linear
bsdf.inputs["Metallic"].default_value   = 0.0
bsdf.inputs["Roughness"].default_value  = 0.4

# Emissive glow (4.x socket names — 3.x used a single "Emission"):
bsdf.inputs["Emission Color"].default_value    = (0.9, 0.3, 0.05, 1.0)
bsdf.inputs["Emission Strength"].default_value = 5.0

obj = bpy.data.objects["HeroSphere"]
if obj.data.materials:
    obj.data.materials[0] = mat                         # replace slot 0
else:
    obj.data.materials.append(mat)                      # first slot
```

## Recipe 4 — Lighting (sun + fill area)

Lights are data + object, like any other. Rotation aims a sun; position matters for
point/area.

```python
import bpy, math
sun_data = bpy.data.lights.new("KeySun", type='SUN')
sun_data.energy = 4.0
sun = bpy.data.objects.new("KeySun", sun_data)
bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0.0, math.radians(30))   # elevation + azimuth

area_data = bpy.data.lights.new("Fill", type='AREA')
area_data.energy, area_data.size = 200.0, 3.0
fill = bpy.data.objects.new("Fill", area_data)
bpy.context.collection.objects.link(fill)
fill.location = (-3.0, -3.0, 2.5)
```

## Recipe 5 — Camera that tracks the subject

```python
import bpy
cam_data = bpy.data.cameras.new("ShotCam")
cam_data.lens = 50.0
cam = bpy.data.objects.new("ShotCam", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (6.0, -6.0, 4.0)
bpy.context.scene.camera = cam                          # make it THE render camera

trk = cam.constraints.new(type='TRACK_TO')              # auto-aim at target
trk.target     = bpy.data.objects["HeroSphere"]
trk.track_axis = 'TRACK_NEGATIVE_Z'                     # camera looks down -Z
trk.up_axis    = 'UP_Y'
```

## Recipe 6 — Render

Prefer the dedicated tool over hand-rolling `bpy.ops.render.render` — it handles the
output path and returns the image:

```
# mcp__blender__render_viewport_to_path   → fast working preview from the viewport
# mcp__blender__render_thumbnail_to_path   → small full render for a quick look
```

Set engine/samples first if quality matters:

```python
import bpy
scn = bpy.context.scene
scn.render.engine = 'CYCLES'          # or 'BLENDER_EEVEE_NEXT' (4.2+) for speed
scn.cycles.samples = 64
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
```

To tie the render loop with critique-and-adjust, hand off to
`blender-mcp-render-review-loop`.

## Verify

- `get_objects_summary` shows your new objects with the **names you set** (no `.001`
  surprises) and expected transforms.
- `get_object_detail_summary` on the shaded object lists your material in its slots.
- A `render_viewport_to_path` image shows the object lit, coloured, and framed as intended.
- No pre-existing object was moved, renamed, or deleted (diff against your first summary).

## Pitfalls

- **Blank material** — you set `default_value` but forgot `mat.use_nodes = True`, so there's
  no node tree and `nodes.get("Principled BSDF")` returns `None` → `AttributeError`.
- **Object never appears** — created with `bpy.data.objects.new(...)` but never
  `collection.objects.link(obj)`. Data exists, scene doesn't show it.
- **Operator "did nothing"** — wrong mode (e.g. in Edit mode) or the required object isn't
  both *active* and *selected*. Set both explicitly between ops on different objects.
- **Stale world matrix** — read `matrix_world` after a move without
  `bpy.context.view_layer.update()`; you get the old value.
- **3.x vs 4.x socket names** — `Emission` (3.x) vs `Emission Color`/`Emission Strength`
  (4.x); `Specular` became `Specular IOR Level` in 4.x. `search_api_docs` if a `KeyError`
  hits on a socket name.
- **Name collision** — reusing an existing name gives you `.001`; later
  `bpy.data.objects["Name"]` still resolves the *old* one. Check the summary first.
- **Wiping the scene** — never call `bpy.ops.wm.read_homefile` or bulk-delete without
  explicit user confirmation. Build additively.
