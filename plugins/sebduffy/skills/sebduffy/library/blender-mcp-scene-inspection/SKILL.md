---
name: blender-mcp-scene-inspection
category: 3d
description: >-
  Read a Blender scene BEFORE editing it — collection/object hierarchy, per-object detail, data-block
  counts, render engine, missing external files, and linked libraries — so edits respect existing
  structure and never clobber names. Use when you need to know what's in a scene, plan a safe edit,
  find a broken/missing texture or library link, audit a handed-over .blend, or answer "what objects
  exist / what modifiers / what materials". Inspect first; the add-on's own rule is NEVER assume
  missing values. Covers both a live session and on-disk .blend files via the *_for_cli summaries.
when_to_use:
  - Before ANY scene edit — build a change plan grounded in the real hierarchy, names, and transforms
  - Auditing a handed-over or unfamiliar .blend to learn its structure, render engine, and asset counts
  - A render is pink/purple or an asset is invisible and you suspect a missing texture, cache, or link
  - Answering "what objects / modifiers / materials / collections exist" without guessing
  - Deciding whether a file uses linked (external) libraries that an edit could break
when_not_to_use:
  - Tools error with connection refused / socket errors — fix the pipe first with blender-mcp-setup
  - You already know the scene and are adding/transforming geometry — use blender-mcp-scene-building
  - Judging whether a render LOOKS right (lighting, framing, materials) — use blender-mcp-render-review-loop
  - Importing PolyHaven/Sketchfab/Hyper3D assets — use blender-mcp-asset-import
  - Looking up a bpy operator/property signature to write code — use blender-mcp-bpy-api-navigator
keywords:
  - blender
  - mcp
  - scene-inspection
  - get_objects_summary
  - object-detail
  - blendfile-summary
  - missing-files
  - linked-libraries
  - datablocks
  - render-engine
  - hierarchy
  - audit
  - safe-edit
  - 3d
similar_to:
  - blender-mcp-setup
  - blender-mcp-scene-building
  - blender-mcp-render-review-loop
  - blender-mcp-asset-import
  - blender-mcp-procedural-generation
  - blender-mcp-bpy-api-navigator
inputs_needed: A live blender-mcp connection (setup green) for the live summaries; OR a path to a .blend file on disk for the *_for_cli summaries; the object name(s) of interest for detail queries
produces: A structured read-only picture of the scene — collection/object tree, per-object detail, data-block counts + render engine, missing-file report, linked-library tree, save/path state — and a safe-edit plan grounded in it
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Blender MCP Scene Inspection

Every safe edit starts by reading the scene. The blender-mcp add-on ships a family of **read-only summary
tools** so you can learn the hierarchy, names, transforms, render engine, and broken references *before*
touching anything. This is not optional politeness — the add-on's own guidance is: **"NEVER assume missing
values — inspect the scene first"** and **"Respect existing structure and naming conventions."** This skill
is the disciplined front half of that loop.

## When to use

Run this before `blender-mcp-scene-building` / `-procedural-generation` on any file you did not just create,
and any time you need ground truth about what exists. It is pure read — none of these tools mutate the scene.

## Prerequisites

- **For live-scene summaries:** a green blender-mcp connection (Blender open, add-on enabled, socket on
  port 9876 connected). If tool calls throw connection/socket errors, stop and run `blender-mcp-setup`.
- **For on-disk summaries:** a path to a `.blend` file. The `*_for_cli` variants run against a file
  headlessly and do not need the interactive session to hold that file open.
- No API keys. These are local introspection tools.

## The two families

| Purpose                        | Live tool                                  | On-disk equivalent                                |
| ------------------------------ | ------------------------------------------ | ------------------------------------------------- |
| Scene tree + objects           | `get_objects_summary`                      | (live only)                                       |
| One object's detail            | `get_object_detail_summary`                | (live only)                                       |
| Data-block counts + engine     | `get_blendfile_summary_datablocks`         | `get_blendfile_summary_datablocks_for_cli`        |
| Missing external files         | `get_blendfile_summary_missing_files`      | `get_blendfile_summary_missing_files_for_cli`     |
| Linked-library tree            | `get_blendfile_summary_of_linked_libraries`| `get_blendfile_summary_of_linked_libraries_for_cli`|
| Path / save status / backups   | `get_blendfile_summary_path_info`          | `get_blendfile_summary_path_info_for_cli`         |
| Guessed use-cases (0–100)      | `get_blendfile_summary_usage_guess`        | `get_blendfile_summary_usage_guess_for_cli`       |

Reach for `execute_blender_code` only when no summary tool answers your question — the server explicitly
marks it a last resort. For read-only probing that IS the fastest path, prefer a tiny `print(...)` over a
scene mutation.

## Recipes

### 1. Standard pre-edit sweep (do this first)

Call these three, in order, to establish the shape of the file:

1. `get_blendfile_summary_path_info` — is it saved? where? how stale? Are there backups if you break it?
2. `get_blendfile_summary_datablocks` — how many meshes/materials/images/collections, active workspace,
   and **which render engine** (Cycles vs EEVEE changes how materials/lighting behave).
3. `get_objects_summary` — the collection hierarchy and every object's name, type, parent, data-block
   name, selection, and visibility.

From that you know the naming scheme to respect, the render context, and the full object inventory —
enough to draft an edit plan that adds to (not overwrites) existing structure.

### 2. Drill into a specific object before transforming it

Never transform an object you haven't read. `get_object_detail_summary` returns type, transforms,
parent, children, modifiers, constraints, materials, visibility, data-block name, and collections:

```
get_object_detail_summary:
  name: "Cube"
```

Watch for these before you edit:
- **Modifiers** — a visible mesh may be driven by a Subdivision/Array/Mirror stack; editing base geometry
  behaves differently than the rendered result.
- **Constraints / parenting** — moving the object may fight a constraint or drag children with it.
- **Shared data-blocks** — if two objects share one mesh data-block (same `data` name), editing the mesh
  changes both instances. The summary surfaces the data name so you can spot the link.

### 3. Diagnose a pink render or invisible asset (missing files)

Magenta/purple surfaces or absent images almost always mean an unresolved external path:

```
get_blendfile_summary_missing_files
```

It reports missing images, libraries, fonts, sounds, movie clips, caches, and sequences. Anything listed
is a broken path to repoint or repack. This is the tool to hit the instant a texture won't show — cheaper
and more precise than eyeballing the render.

### 4. Check for linked libraries before a structural edit

Linked (as opposed to appended) data lives in another `.blend` and is read-only in this file; a "safe"
rename or delete can silently break the link or fail:

```
get_blendfile_summary_of_linked_libraries
```

It returns the tree of directly and indirectly linked library files. If the object you're about to edit
comes from a linked library, plan a *library override* or edit the source file instead of mutating in place.

### 5. Audit an unfamiliar / handed-over file (on disk, no live edit)

To characterise a `.blend` you were handed without opening and altering it, use the `*_for_cli` summaries.
Get its intended purpose first, then its contents and health:

```
get_blendfile_summary_usage_guess_for_cli      # scored 0–100 guesses of what the file is for
get_blendfile_summary_datablocks_for_cli
get_blendfile_summary_missing_files_for_cli
get_blendfile_summary_of_linked_libraries_for_cli
get_blendfile_summary_path_info_for_cli
```

(The exact path argument the `_for_cli` tools expect is defined by their schema — pass the `.blend` path
as documented when you load the tool.) `usage_guess` is a fast orientation for "is this a character rig, a
product-viz scene, a motion-graphics file…" before you commit reading time.

## Verify

Inspection is verified by *acting on what it returned*, not by a status code:

- After `get_objects_summary`, your edit plan names **real** objects/collections from the output — never a
  guessed name. Cross-check a target with `get_object_detail_summary` and confirm its type/data-block
  match your assumption before mutating.
- After `get_blendfile_summary_missing_files`, an **empty** report means no broken external refs; a
  non-empty one is your fix list — re-run it after repointing paths and confirm it's now empty.
- After `get_blendfile_summary_datablocks`, echo the render engine into your plan so material/lighting
  choices match (Cycles vs EEVEE).

## Pitfalls

- **Editing before reading = clobbered work.** Skipping the sweep and assuming a name (`"Cube"`, `"Camera"`)
  is the #1 way to overwrite or duplicate existing structure. Inspect, then edit.
- **Live vs on-disk confusion.** The plain summaries read the *currently open* scene; `*_for_cli` variants
  read a file on disk. If numbers look wrong, confirm which file you're actually querying — an unsaved live
  session and its last-saved `.blend` differ.
- **Ignoring shared data-blocks.** Two objects pointing at one mesh/material data-block means an edit hits
  both. `get_object_detail_summary` shows the data name — check it before assuming instances are independent.
- **Treating linked libraries as editable.** Linked data is read-only here. Renaming/deleting it in this
  file breaks the link; edit the source `.blend` or set up a library override.
- **Missing-files report shows paths, not fixes.** It tells you *what* is broken, not where the asset moved.
  Repoint (`bpy` `image.filepath` / *Find Missing Files*) or repack, then re-run to confirm clean.
- **Over-reaching with execute_blender_code.** For read-only questions a summary tool already answers, the
  raw-code tool is slower and riskier (easy to mutate by accident). Use it only when nothing else fits, and
  keep it to `print`-style probes.
- **Stale summary after your own edits.** These are point-in-time snapshots. After you mutate the scene,
  re-run the relevant summary rather than trusting an earlier read.
