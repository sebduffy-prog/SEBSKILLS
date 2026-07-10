---
name: blender-mcp-bpy-api-navigator
category: 3d
description: >-
  Write correct bpy the FIRST time instead of guessing — resolve the exact operator argument
  names, property paths, and enum string values against the bundled Blender Python API + manual
  before running any execute_blender_code. Use when a bpy call throws TypeError/KeyError/enum-not-
  found/RuntimeError context-incorrect, when you need an operator or property signature, when an
  enum value must be exact ('CYCLES', 'GLOSSY'), or when an operator silently does nothing because
  its poll() failed. Look it up with search_api_docs / get_python_api_docs; do not invent APIs.
when_to_use:
  - Before writing a non-trivial bpy snippet — confirm operator arg names, property paths, and enum spellings
  - A call errored — TypeError (bad kwarg), KeyError (socket/enum name), or "expected a string in enum"
  - An operator returned {'CANCELLED'} or did nothing — its poll() context requirement was unmet
  - You need the exact identifier for a property (e.g. scene.cycles.samples) or a class's members
  - Porting 3.x code to 4.x (or back) where socket/property names changed and need verifying
when_not_to_use:
  - Tools error with connection refused / broken pipe — fix the pipe first with blender-mcp-setup
  - You just need to read what objects/materials exist in the scene — use blender-mcp-scene-inspection
  - Adding geometry/materials with already-known APIs — use blender-mcp-scene-building
  - Importing PolyHaven/Sketchfab/Hyper3D assets — use blender-mcp-asset-import
  - Judging whether a render LOOKS right — use blender-mcp-render-review-loop
keywords:
  - blender
  - bpy
  - python-api
  - search_api_docs
  - get_python_api_docs
  - search_manual_docs
  - operator
  - enum
  - poll
  - context
  - override
  - typeerror
  - keyerror
  - signature
  - 3d
similar_to:
  - blender-mcp-setup
  - blender-mcp-scene-building
  - blender-mcp-scene-inspection
  - blender-mcp-render-review-loop
  - blender-mcp-asset-import
  - blender-mcp-procedural-generation
inputs_needed: A green blender-mcp connection (for execute_blender_code round-trips); the bpy identifier, operator, or enum you need to resolve; the error text if a prior call failed
produces: The verified operator/property signature, exact enum string values, and context/poll requirements — plus a corrected, runnable bpy snippet that executes without guesswork
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Blender MCP bpy API Navigator

The single biggest source of wasted Blender turns is guessed API: a wrong kwarg name, a
mis-spelled enum, a property that moved between 3.x and 4.x, or an operator whose `poll()`
quietly cancels. The blender-mcp add-on **bundles the full Blender Python API reference and
user manual as searchable RST** — so you never have to guess. Look it up, then write it once.

## When to use

Reach for this the moment you are about to write bpy you are not 100% sure of, or the moment a
call throws `TypeError` / `KeyError` / `RuntimeError` / `enum ... not found`. It pairs with
`blender-mcp-scene-building` and `-procedural-generation` (they write; this de-risks the write).

## Prerequisites

- A green blender-mcp connection if you want to *run* the snippet (`execute_blender_code`).
  The doc tools themselves are **read-only over bundled RST** and work even without a live
  Blender, but running your verified code needs the socket up — see `blender-mcp-setup`.
- No API keys. `search_api_docs`, `get_python_api_docs`, and `search_manual_docs` are local.

## The three lookup tools

| Tool                    | Use for                                                              |
| ----------------------- | ------------------------------------------------------------------- |
| `search_api_docs`       | Fuzzy full-text over the API RST — "how do I set cycles samples"     |
| `get_python_api_docs`   | Exact fetch by identifier — `bpy.ops.mesh.primitive_cube_add`        |
| `search_manual_docs`    | Concepts/workflow from the user manual — "what is a shape key"       |

Search is token-based and case-insensitive; every token must appear (stop-words dropped).
Regex is not supported. Bump `context` to pull surrounding paragraphs into a hit.

## Recipe 1 — resolve an operator's arguments before calling it

Never trust remembered kwargs. Fetch the exact signature:

```
get_python_api_docs(identifier="bpy.ops.mesh.primitive_cube_add")
```

The `content` lists every parameter with its type and default (e.g. `size`, `location`,
`rotation`, `scale`, `align` enum). Copy the names verbatim — a typo'd kwarg raises
`TypeError: ... unexpected keyword argument`. If you only half-remember the name, search:

```
search_api_docs(query="primitive add cylinder vertices radius depth")
```

Then run it against the live scene:

```
execute_blender_code(code="""
import bpy
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.5, depth=2.0, location=(0,0,1))
result = {"active": bpy.context.active_object.name}
""")
```

## Recipe 2 — get an enum's EXACT string values

Enum properties reject anything not in their set (`TypeError: enum "X" not found in (...)`).
Fetch the property doc to see the allowed literals — do not guess casing:

```
get_python_api_docs(identifier="bpy.types.RenderSettings.engine")
```

Confirms `'BLENDER_EEVEE_NEXT'` (4.2+), `'BLENDER_WORKBENCH'`, `'CYCLES'` — note EEVEE was
renamed from `'BLENDER_EEVEE'` in 4.2. If the doc is unclear, the live scene is ground truth:

```
execute_blender_code(code="""
import bpy
prop = bpy.types.RenderSettings.bl_rna.properties['engine']
result = {"items": [i.identifier for i in prop.enum_items]}
""")
```

That `bl_rna ... enum_items` pattern dumps the exact accepted strings for **any** enum
(blend modes, node types, modifier types, constraint types) — use it whenever a doc lag is
suspected against the installed version.

## Recipe 3 — discover a namespace / drill to a property path

Use trailing-`*` to enumerate children when you don't know the full path:

```
get_python_api_docs(identifier="bpy.*")               # top-level: app, context, data, ops, types...
get_python_api_docs(identifier="bpy.context.*")       # what's on context
get_python_api_docs(identifier="bpy.types.Scene.*")   # scene sub-properties
```

Then fetch the leaf exactly, e.g. `bpy.types.CyclesRenderSettings.samples`. A `"partial"`
response (found=False) means the tail isn't in that RST but lists near-miss siblings in
`submodules` — follow those to the real name rather than inventing one.

## Recipe 4 — fix an operator that "did nothing" (poll / context)

An operator that returns `{'CANCELLED'}` or no-ops usually failed its `poll()`: wrong mode,
or no active/selected object of the required type. First read *why* — many `bpy.ops` docs
state the context they need. Then set that context explicitly before calling:

```
execute_blender_code(code="""
import bpy
obj = bpy.data.objects['Cube']
bpy.context.view_layer.objects.active = obj      # active AND
obj.select_set(True)                             # selected
bpy.ops.object.mode_set(mode='EDIT')             # correct mode
# ... edit-mode op here ...
bpy.ops.object.mode_set(mode='OBJECT')
result = {"ok": True}
""")
```

If it still cancels, pass a **context override** (Blender 4.x API):

```
execute_blender_code(code="""
import bpy
win = bpy.context.window
area = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
with bpy.context.temp_override(window=win, area=area, region=region):
    bpy.ops.view3d.snap_cursor_to_selected()
result = {"ok": True}
""")
```

Search the manual for the operator's concept if the requirement is still unclear:
`search_manual_docs(query="snap cursor to selected")`.

## Verify

- The identifier you fetched returned `kind: "exact"` or `"definition"` with real `content`
  — not `"partial"` (that means the name is wrong; use its `submodules` near-misses).
- Enum literals you use appear verbatim in the doc **or** in the live `enum_items` dump.
- The snippet runs via `execute_blender_code` and its `result` dict confirms the intended
  effect (object created, property set) with no traceback in the response.
- After property writes that feed computed values, `bpy.context.view_layer.update()` before
  reading `matrix_world` / modifier output.

## Pitfalls

- **Trusting memory over the doc.** API names drift across versions; a 30-second lookup beats
  a cancelled turn. If you "know" a kwarg, you still risk a version rename — verify.
- **3.x vs 4.x renames.** `'BLENDER_EEVEE'` → `'BLENDER_EEVEE_NEXT'` (4.2); Principled BSDF
  socket `Emission` → `Emission Color`/`Emission Strength`, `Specular` → `Specular IOR Level`.
  A `KeyError` on a socket/enum name is almost always this — re-fetch for the running version.
- **Enum casing.** Enums are case-sensitive uppercase literals (`'CYCLES'`, not `'cycles'`).
- **Assuming poll passed.** `bpy.ops` returns a set; check for `{'CANCELLED'}`. Silent no-op =
  unmet context, not success. Set active + selected + mode, or `temp_override`.
- **Large RST truncation.** Files over 32 KB return a summary instead of full `content` with
  empty `examples` — re-query the specific member (e.g. one method) to get its rendered block.
- **execute_blender_code without `result`.** To read data back, assign a JSON-serialisable
  dict to a variable named exactly `result`; otherwise you get nothing useful returned.
- **Reaching for code when a tool exists.** `execute_blender_code` is the last resort — if a
  dedicated blender-mcp tool (summaries, screenshots, render) does the job, prefer it.
