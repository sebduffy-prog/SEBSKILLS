---
name: comfyui-workflow-runner
category: media
description: >
  Headlessly execute a ComfyUI workflow from the command line via its HTTP + WebSocket API —
  POST the API-format node graph to /prompt, track progress over ws?clientId=, then pull the
  finished images from /history and /view. Use when someone says "run my ComfyUI workflow from
  a script", "run a ComfyUI graph headless / on the server", "batch-generate over a CSV of
  prompts", "queue a workflow_api.json", "call ComfyUI without the browser UI", "loop a
  Stable-Diffusion / Flux / SDXL node graph over many prompts or seeds", or "drive ComfyUI
  custom nodes / LoRAs from Python". Covers export API JSON, submit, poll, download, and
  editing node inputs (prompt text, seed, filename) per run.
when_to_use:
  - Run an existing ComfyUI workflow from the terminal with no browser open
  - Batch-generate images by looping one workflow over a CSV of prompts / seeds
  - Override specific node inputs each run (positive prompt, seed, steps, filename prefix)
  - Kick a ComfyUI graph off a server / CI and collect the output files
  - Queue many jobs and retrieve each result by prompt_id from /history
  - Drive a graph that uses custom nodes, LoRAs, or ControlNet you already wired in the UI
when_not_to_use:
  - You just want a single text-to-image with a hosted API, no node graph → use flux-image-gen or nano-banana-image
  - You want image-to-video / animated clips end to end → use video-gen-pipeline
  - You need to upscale or restore an existing image, not run a graph → use ai-upscale-restore
  - You only need background cutout on a batch of images → use background-removal-batch
  - You want plain ffmpeg encode/transcode of media → use ffmpeg-cookbook or batch-transcode-encode
keywords: [comfyui, comfy, workflow_api.json, api format, /prompt, client_id, prompt_id, websocket, ws clientId, /history, /view, node graph, headless, batch prompts, csv, stable diffusion, sdxl, flux, lora, controlnet, custom nodes, queue prompt, save api format]
similar_to: [flux-image-gen, nano-banana-image, video-gen-pipeline, ai-upscale-restore, background-removal-batch]
inputs_needed:
  - The workflow in API format (workflow_api.json) — exported via ComfyUI Dev Mode "Save (API Format)"
  - The ComfyUI server address (default 127.0.0.1:8188) and that it is running
  - Which node IDs / input fields to override per run (e.g. the positive-prompt node, the KSampler seed)
  - For batch: a CSV whose columns map to those overrides
produces: Generated image/output files pulled from the ComfyUI server into a local output dir, one per queued prompt
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# ComfyUI Workflow Runner (headless HTTP + WebSocket API)

ComfyUI runs headless by default — the browser UI is just one WebSocket client. Any HTTP client
can POST a workflow to `/prompt` and fetch the outputs. Two jobs this skill covers: (1) run one
graph from the CLI, (2) loop that graph over a CSV of prompts/seeds.

## When to use

Reach for this when the graph already exists in ComfyUI (custom nodes, LoRAs, ControlNet all
wired) and you want to fire it repeatedly without clicking Queue. If you just need one hosted
text-to-image, `flux-image-gen` is simpler.

## Prerequisites

- **A running ComfyUI server.** Start it headless: `python main.py --listen 127.0.0.1 --port 8188`.
  Confirm with `curl -s http://127.0.0.1:8188/system_stats | head -c 200`.
- **The workflow in API format**, not the editor `.json`. In ComfyUI enable Dev Mode
  (Settings → gear → "Enable Dev mode Options"), then use the **"Save (API Format)"** button →
  `workflow_api.json`. This strips UI-only metadata (node positions, colours, groups) and keys
  nodes by ID with their `class_type` + `inputs` — the shape `/prompt` expects.
- **Python 3** with `requests` and `websocket-client` (`pip install requests websocket-client`).
  Both are pure-Python; no brew/ffmpeg needed for API calls. (ffmpeg only matters if a node
  itself outputs video — see media-toolchain-bootstrap for the portable ffmpeg binary.)
- The output files land in ComfyUI's `output/` dir on the server; you retrieve copies via `/view`.

## API shape (the three endpoints)

- `POST /prompt` — body `{"prompt": <api_json>, "client_id": "<uuid>"}`. Returns `{"prompt_id": "..."}`.
  Optional `"prompt_id"` to set your own id. Invalid graphs return HTTP 400 with a `node_errors` map.
- `GET /history/{prompt_id}` — after completion, `["<id>"]["outputs"][<node_id>]["images"]` lists
  `{filename, subfolder, type}` for each saved image.
- `GET /view?filename=..&subfolder=..&type=output` — returns the raw image bytes.
- `WS /ws?clientId=<uuid>` — stream of JSON messages. Execution is **done** when you see
  `{"type":"executing","data":{"node":null,"prompt_id":"<yours>"}}`. Binary frames are live latent
  previews (ignore them). Polling `/history` also works if you skip the socket.

## Recipe 1 — run one workflow, override a couple of inputs

Use the helper script (writes each output image to `--out`):

```bash
python scripts/comfy_run.py \
  --server 127.0.0.1:8188 \
  --workflow workflow_api.json \
  --set 6.inputs.text="a neon koi carp, cinematic" \
  --set 3.inputs.seed=42 \
  --out ./out
```

`--set NODEID.inputs.FIELD=VALUE` patches the API JSON before submit. Values that parse as int/float/JSON
are coerced; otherwise treated as a string. Find the node IDs by opening `workflow_api.json` — each
top-level key is a node ID; look for the `CLIPTextEncode` node for prompt text and `KSampler` for
`seed`/`steps`/`cfg`.

Inspect node IDs quickly:

```bash
python -c "import json,sys; d=json.load(open('workflow_api.json')); [print(k, d[k]['class_type']) for k in d]"
```

## Recipe 2 — batch over a CSV of prompts

CSV header = the `--set` paths, one row per run. Example `prompts.csv`:

```csv
6.inputs.text,3.inputs.seed,9.inputs.filename_prefix
"a neon koi carp, cinematic",42,koi
"a brutalist cathedral at dusk",99,cathedral
"a bowl of ramen, macro",7,ramen
```

Run every row:

```bash
python scripts/comfy_run.py --server 127.0.0.1:8188 \
  --workflow workflow_api.json --csv prompts.csv --out ./out
```

The script queues each row (each gets a fresh `client_id`+`prompt_id`), waits for completion over
the WebSocket, then downloads that row's images named by prompt_id (and the row's
`filename_prefix` if present).

## Minimal inline version (no script)

If you only need one submit + poll and don't want the helper:

```bash
CID=$(python -c "import uuid;print(uuid.uuid4())")
PID=$(curl -s -X POST http://127.0.0.1:8188/prompt \
  -H 'Content-Type: application/json' \
  -d "{\"client_id\":\"$CID\",\"prompt\":$(cat workflow_api.json)}" \
  | python -c "import sys,json;print(json.load(sys.stdin)['prompt_id'])")
echo "queued $PID"
# poll history until the key appears, then list output images:
until curl -s http://127.0.0.1:8188/history/$PID | grep -q '"images"'; do sleep 1; done
curl -s http://127.0.0.1:8188/history/$PID \
  | python -c "import sys,json;h=json.load(sys.stdin)[__import__('os').environ['PID']]['outputs'];\
[print(i['filename']) for n in h.values() for i in n.get('images',[])]" PID=$PID
```

(For real work prefer the script — it handles the socket, coercion, and download.)

## Verify

- `curl -s http://127.0.0.1:8188/system_stats` returns JSON → server is up.
- After a run, the script prints `saved ./out/<name>.png` per image; `ls -la ./out` shows non-zero files.
- `file ./out/*.png` reports `PNG image data` with sane dimensions.
- A 400 on `/prompt` means a bad graph — read the returned `node_errors`; usually a missing model
  file or an override pointing at a node ID that doesn't exist.

## Pitfalls

- **Wrong JSON export.** The editor's normal "Save" produces UI JSON (`nodes`/`links` arrays) that
  `/prompt` rejects. You MUST use **Save (API Format)** → the flat `{"<id>": {class_type, inputs}}` map.
- **Seed not changing.** ComfyUI caches unchanged nodes; if you re-run without touching the seed you
  get the cached image back instantly. Always vary `KSampler.inputs.seed` per batch row.
- **Node ID vs class.** `--set` targets a node **ID** (a number-string key), not the class name. Two
  `CLIPTextEncode` nodes (positive/negative) have different IDs — patch the right one.
- **Missing models/custom nodes.** The graph references checkpoints/LoRAs/custom nodes by name; they
  must exist on the server or you get 400 `node_errors`. This skill runs graphs, it doesn't install nodes.
- **Long jobs / no socket.** If you skip the WebSocket, poll `/history/{id}` (not `/queue`) for the
  `outputs` key. Give big SDXL/Flux graphs a generous timeout.
- **`filename_prefix` collisions.** Reusing the same prefix appends counters server-side; the script
  downloads whatever `/history` reports, so distinct prefixes per row keep outputs sortable.

Sources: [ComfyUI websockets_api_example.py](https://github.com/comfyanonymous/ComfyUI/blob/master/script_examples/websockets_api_example.py) · [Workflow API Format (docs.comfy.org)](https://docs.comfy.org/development/api-development/workflow-api-format)
