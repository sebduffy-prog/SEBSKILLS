---
name: blender-mcp-procedural-generation
category: 3d
description: >
  Generate PARAMETRIC content in a live Blender session over MCP — build Geometry Nodes
  trees, stack modifiers (Array / Subsurf / Bevel / Solidify / Screw), and scatter/instance
  objects across a surface with tweakable, re-runnable parameters. Reach for this when
  someone says "scatter rocks/grass over the terrain", "array this N times", "make it
  procedural / node-based", "distribute points on faces", "instance on points", "add a
  bevel/subsurf/solidify modifier", "hair particles as scatter", or "expose a knob I can
  tune". Everything runs through `execute_blender_code` because there is NO dedicated GN
  tool — so the bpy MUST be 4.x-correct: interface.new_socket, modifier[socket.identifier],
  depsgraph update before reading results. Inspect first, mutate additively, seed randomness.
when_to_use:
  - "Scattering / instancing many copies of an object over a mesh surface (rocks, grass, props)"
  - "Building a Geometry Nodes tree from scratch and exposing named parameters as modifier inputs"
  - "Adding non-destructive modifiers (Array, Subsurf, Bevel, Solidify, Screw, Mirror) to an object"
  - "Setting or animating a geometry-nodes input value by its socket identifier"
  - "Particle-system hair scatter as a lightweight alternative to a full GN instancer"
  - "Any 'make it parametric / procedural / re-runnable with a knob' request over the blender MCP"
when_not_to_use:
  - "MCP server not connected / add-on off → blender-mcp-setup first"
  - "One-off static objects, materials, lights, camera, a single render → blender-mcp-scene-building"
  - "Only READING what's in the scene (list objects, dump a node tree) → blender-mcp-scene-inspection"
  - "Render-then-critique-then-adjust visual iteration loop → blender-mcp-render-review-loop"
  - "Importing a finished asset instead of generating one → blender-mcp-asset-import"
keywords: [blender mcp, geometry nodes, geometrynodetree, procedural, modifier stack, array modifier, subsurf, bevel, solidify, scatter, instance on points, distribute points on faces, particle system, interface new_socket, node group, parametric, bpy, execute_blender_code]
similar_to: [blender-mcp-setup, blender-mcp-scene-building, blender-mcp-scene-inspection, blender-mcp-render-review-loop, blender-mcp-asset-import, blender-mcp-bpy-api-navigator]
inputs_needed:
  - "A running Blender (4.x) with the MCP add-on connected (mcp__blender__* tools available)"
  - "The base surface/object to operate on, and the object(s) to instance/scatter (by name)"
  - "The parameters to expose or values to set: count, density, seed, scale range, bevel width, etc."
produces: Geometry Nodes trees, modifier stacks, and scatter/instancing setups on live objects — parametric and re-runnable — plus optional exposed modifier inputs you can retune
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Procedural / Parametric Generation in Blender over MCP

## When to use

You are connected to Blender through `mcp__blender__*` and need to generate content
**parametrically** — Geometry Nodes, a modifier stack, or a scatter/instance system — so
the result is driven by named knobs you can retune and re-run, not baked one-off geometry.

There is **no dedicated geometry-nodes or modifier MCP tool**: the server only gives you
`execute_blender_code`. So this skill is about writing bpy that is *correct for Blender 4.x*
— where the node-group interface API changed and geometry-nodes modifier inputs are keyed by
socket *identifier*, not name.

## Prerequisites

- Blender **4.x** running with the MCP add-on **connected**. If calls error with "not
  connected", stop and run `blender-mcp-setup`.
- Deferred tools loaded — batch in one call:
  `ToolSearch "select:mcp__blender__get_objects_summary,mcp__blender__get_object_detail_summary,mcp__blender__execute_blender_code,mcp__blender__render_viewport_to_path,mcp__blender__search_api_docs"`
- The **4.x** node interface API. In 4.0+ the old `node_group.inputs.new(...)` /
  `outputs.new(...)` are **gone** — you MUST use `node_group.interface.new_socket(name,
  in_out=..., socket_type=...)`. If unsure of a node/socket name, `search_api_docs` before
  guessing.

## Three rules that prevent most breakage

1. **Inspect before you mutate.** `get_objects_summary` first — confirm the base object and
   the instanced object exist by the exact names you'll reference. A missing name raises
   `KeyError`; a duplicate silently became `.001`.
2. **Geometry-nodes inputs are keyed by IDENTIFIER, not label.** After exposing a socket,
   set its value with `mod[socket.identifier] = value` (identifiers look like `"Socket_2"`),
   NOT `mod["Count"]`. Read the identifier off the interface item you created.
3. **Update the depsgraph before reading procedural results.** Geometry Nodes and modifiers
   are lazily evaluated — `bpy.context.view_layer.update()` (or read via the evaluated
   depsgraph) before you inspect counts, bounds, or the realized mesh.

## Recipe 1 — Modifier stack (non-destructive, no nodes)

The simplest parametric win. Modifiers are added by `type` and tuned by attribute; the stack
order is the list order, top → bottom.

```python
import bpy
obj = bpy.data.objects["Base"]                     # inspect first; must exist

arr = obj.modifiers.new(name="Array", type='ARRAY')
arr.count = 6                                        # the knob
arr.relative_offset_displace = (1.2, 0.0, 0.0)      # 1.2 x bbox in X

bev = obj.modifiers.new(name="Bevel", type='BEVEL')
bev.width, bev.segments = 0.02, 3

sub = obj.modifiers.new(name="Subsurf", type='SUBSURF')
sub.levels = 2                                       # viewport
sub.render_levels = 3

sol = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
sol.thickness = 0.05
```

Retune later by name; the stack re-evaluates automatically:

```python
bpy.data.objects["Base"].modifiers["Array"].count = 12
```

Bake to real geometry ONLY when asked (this is destructive — needs active+selected):

```python
import bpy
bpy.ops.object.select_all(action='DESELECT')
o = bpy.data.objects["Base"]; o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.object.modifier_apply(modifier="Array")
```

## Recipe 2 — Build a Geometry Nodes tree with an exposed parameter

Create a `GeometryNodeTree`, declare its interface (4.x API), wire Group Input → work →
Group Output, attach it to a `'NODES'` modifier, then drive it by socket identifier.

```python
import bpy

obj = bpy.data.objects["Base"]

# 1. Node group + REQUIRED interface sockets (4.x: interface.new_socket, not inputs.new)
ng = bpy.data.node_groups.new("ProcGrid", 'GeometryNodeTree')
geo_in  = ng.interface.new_socket("Geometry", in_out='INPUT',  socket_type='NodeSocketGeometry')
geo_out = ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
count   = ng.interface.new_socket("Count",    in_out='INPUT',  socket_type='NodeSocketInt')
count.default_value, count.min_value = 5, 1     # exposed knob with a floor

# 2. Nodes: group I/O + a simple transform/instance step
nodes, links = ng.nodes, ng.links
n_in  = nodes.new('NodeGroupInput');  n_in.location  = (-400, 0)
n_out = nodes.new('NodeGroupOutput'); n_out.location = ( 400, 0)
# Minimal pass-through so the tree is valid; replace middle with real work:
links.new(n_in.outputs["Geometry"], n_out.inputs["Geometry"])

# 3. Attach as a Geometry Nodes modifier
mod = obj.modifiers.new(name="GeoNodes", type='NODES')
mod.node_group = ng

# 4. Set the exposed input BY IDENTIFIER (not by label "Count")
mod[count.identifier] = 9                        # e.g. "Socket_2"
bpy.context.view_layer.update()                  # evaluate before reading results
```

`count.identifier` is the reliable key. If you only have the modifier later, discover it:

```python
for item in mod.node_group.interface.items_tree:
    if getattr(item, "in_out", None) == 'INPUT':
        print(item.name, "->", item.identifier)   # map labels to identifiers
```

## Recipe 3 — Scatter / instance via Geometry Nodes (the good way)

Distribute points on the base surface, then instance a collection or object on them, with a
**seed** for reproducibility. This is the modern, non-destructive scatter.

```python
import bpy

surface  = bpy.data.objects["Terrain"]           # emitter surface (a mesh)
instance = bpy.data.objects["Rock"]              # object to scatter

ng = bpy.data.node_groups.new("Scatter", 'GeometryNodeTree')
ng.interface.new_socket("Geometry", in_out='INPUT',  socket_type='NodeSocketGeometry')
ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
n_in  = ng.nodes.new('NodeGroupInput');  n_in.location  = (-600, 0)
n_out = ng.nodes.new('NodeGroupOutput'); n_out.location = ( 600, 0)

dist = ng.nodes.new('GeometryNodeDistributePointsOnFaces'); dist.location = (-200, 0)
dist.inputs["Density"].default_value = 8.0        # points per m^2 — the density knob
dist.inputs["Seed"].default_value    = 3          # reproducible layout

iop  = ng.nodes.new('GeometryNodeInstanceOnPoints'); iop.location = (200, 0)
objinfo = ng.nodes.new('GeometryNodeObjectInfo');    objinfo.location = (0, -250)
objinfo.inputs["Object"].default_value = instance
objinfo.transform_space = 'RELATIVE'

L = ng.links
L.new(n_in.outputs["Geometry"],   dist.inputs["Mesh"])
L.new(dist.outputs["Points"],     iop.inputs["Points"])
L.new(objinfo.outputs["Geometry"], iop.inputs["Instance"])
# align + random scale off the distribution's outputs:
L.new(dist.outputs["Rotation"],   iop.inputs["Rotation"])
L.new(iop.outputs["Instances"],   n_out.inputs["Geometry"])

mod = surface.modifiers.new(name="Scatter", type='NODES')
mod.node_group = ng
bpy.context.view_layer.update()
```

Randomise instance scale by inserting a `FunctionNodeRandomValue` (type `FLOAT`, seeded)
into `iop.inputs["Scale"]`. Keep the same seed for a stable layout across re-runs.

## Recipe 4 — Particle-system hair scatter (lightweight alternative)

When you don't need a node tree, a hair particle system scatters an object cheaply.

```python
import bpy
surface = bpy.data.objects["Terrain"]
psmod = surface.modifiers.new(name="GrassScatter", type='PARTICLE_SYSTEM')
ps    = surface.particle_systems[-1]
s     = ps.settings
s.type          = 'HAIR'
s.count         = 500
s.hair_length   = 0.2
s.seed          = 7                               # reproducible
s.render_type   = 'OBJECT'
s.instance_object = bpy.data.objects["GrassBlade"]
s.particle_size = 1.0
s.size_random   = 0.4                             # scale variation
bpy.context.view_layer.update()
```

## Verify

- `get_object_detail_summary` on the target lists your modifier(s) (`Array`, `GeoNodes`,
  `Scatter`, `GrassScatter`) in stack order.
- For GN: iterate `mod.node_group.interface.items_tree` and confirm the exposed sockets and
  that `mod[identifier]` returns the value you set.
- Count realized geometry off the **evaluated** object, not the source:

  ```python
  import bpy
  dg = bpy.context.evaluated_depsgraph_get()
  ev = bpy.data.objects["Terrain"].evaluated_get(dg)
  print(len(ev.data.vertices))                    # grows once scatter is live
  ```

- `render_viewport_to_path` shows instances distributed as intended; hand to
  `blender-mcp-render-review-loop` for look iteration.
- Re-running with the same `Seed` reproduces the identical layout (proves it's parametric,
  not random each eval).

## Pitfalls

- **`inputs.new` / `outputs.new` `AttributeError`** — that's the pre-4.0 API. Use
  `ng.interface.new_socket(name, in_out=..., socket_type=...)` in 4.x.
- **Setting a GN input does nothing** — you keyed it by label (`mod["Count"]`) instead of
  identifier (`mod[socket.identifier]`, e.g. `"Socket_2"`). Only the identifier works.
- **Empty / broken GN result** — a `GeometryNodeTree` needs a Group Output whose Geometry
  input is actually linked. An unconnected output realizes nothing.
- **Reading stale counts** — Geometry Nodes and modifiers evaluate lazily. Call
  `bpy.context.view_layer.update()` and read via `evaluated_get(depsgraph)`, not the source
  mesh, or you'll see the un-scattered original.
- **Non-reproducible scatter** — leaving Seed at 0/default or re-seeding each run makes the
  layout jump every evaluation. Set an explicit `Seed` and keep it fixed.
- **Modifier order matters** — Subsurf before Bevel vs after gives different edges; reorder
  the stack (or add in the right sequence) rather than fighting the result.
- **Instanced object also renders at origin** — the source `Rock`/`GrassBlade` is still a
  visible scene object. Move it to a hidden collection (or set it non-renderable) if you only
  want the instances.
- **Applying too early** — `modifier_apply` bakes and is destructive; keep it procedural
  unless the user explicitly wants it flattened, and never bulk-apply without confirmation.
