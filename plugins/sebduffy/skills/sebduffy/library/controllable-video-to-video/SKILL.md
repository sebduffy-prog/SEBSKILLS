---
name: controllable-video-to-video
category: media
description: >
  Restyle, relight, recompose, or VFX an EXISTING clip while keeping its motion —
  video-to-video, not fresh generation. Trigger when someone says "make this footage
  look like anime / claymation / golden hour", "relight this plate", "change the season
  or weather in this shot", "add/remove an object from this video", "restyle our ad in
  a new look", "put our logo on the wall in this clip", or "new camera angle of the same
  scene". Grounded on Runway Gen-4 Aleph (official REST API) with Wan 2.6, Replicate, and
  AI/ML API as alternate backends. Public-URL/data-URI input, poll-to-download.
when_to_use:
  - Restyling live footage into another look (anime, claymation, oil-paint, brand palette) while preserving the original motion and timing
  - Relighting a plate (golden hour, night, studio key) or changing season/weather/time-of-day without a reshoot
  - Adding, removing, or replacing objects/props/text in an existing clip, or greenscreen-free set extension
  - Generating an alternate camera angle or the next shot of the SAME scene from a reference clip
  - Producing quick brand-restyle variants of an ad cut for social or client review
  - Batch-restyling many short clips through one scriptable API call
when_not_to_use:
  - Generating video from a still image or pure text with no source clip → use video-gen-pipeline
  - Assembling, trimming, or reframing existing footage without AI transformation → use social-video-reframe or video-clip-extractor
  - Frame-rate / slow-motion / interpolation work → use frame-interpolation-retiming
  - Upscaling or restoring degraded footage → use ai-upscale-restore
  - Removing only the background for compositing → use background-removal-batch
keywords:
  - video-to-video
  - v2v
  - restyle
  - relight
  - runway
  - gen-4-aleph
  - aleph
  - wan-2.6
  - recompose
  - vfx
  - style-transfer
  - object-removal
  - replicate
  - footage-transform
  - season-change
similar_to:
  - video-gen-pipeline
  - flux-image-gen
  - nano-banana-image
  - ai-upscale-restore
  - social-video-reframe
inputs_needed: A source clip as a public HTTPS URL, a data URI, or a local file; a text edit prompt; and one API key (RUNWAYML_API_SECRET, REPLICATE_API_TOKEN, or a provider key). Optional style reference image and seed.
produces: A transformed MP4 (same motion/timing as the source, new look/lighting/content) downloaded locally, plus the task id and hosted output URL from the backend.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Controllable Video-to-Video (restyle / relight / recompose)

Transform footage you already have. Unlike text-to-video or image-to-video (which
invent new motion), **video-to-video (v2v)** takes a source clip as the structural
anchor and re-renders it under a prompt — so the camera move, timing, and staging
survive while the *look* or *content* changes. This is the fast lane for "same ad,
new style", relights, weather swaps, and object add/remove without a reshoot.

## When to use

Reach for this when the deliverable must keep the original clip's motion but change
its appearance: anime/claymation restyle, golden-hour relight, winter→summer, remove
a logo, add rain, or a fresh angle on the same scene. If there is **no** source clip,
you want plain generation — use `video-gen-pipeline` instead.

## Prerequisites

Pick ONE backend. Runway Gen-4 Aleph is the reference implementation (best control);
the others are drop-in alternates.

| Backend | Model | Auth env var | Notes |
|---|---|---|---|
| Runway (official) | `gen4_aleph` | `RUNWAYML_API_SECRET` | REST API, this skill's helper. ~15 credits/sec. |
| Replicate | `runwayml/gen4-aleph` | `REPLICATE_API_TOKEN` | Same model, simplest polling. |
| AI/ML API | `runway/gen4_aleph` | `AIMLAPI_KEY` | `POST /v2/video/generations`. |
| Alibaba Wan | Wan 2.6 v2v | provider key (WaveSpeed / Atlas / DashScope) | Strong anime/live-action restyle, native audio, up to ~15 s / 1080p. |

- **macOS note**: the helper is pure stdlib, so stock `python3` (3.9) runs it — no pip, no brew.
- **Input hosting**: Runway/AI-ML fetch the clip, so it must be a public HTTPS URL or a
  `data:` URI. The helper base64-inlines a **local file** for you, but large clips are
  better uploaded first (S3, R2, `gh release upload`, or a signed URL).
- **Keep clips short** (a few seconds). Aleph is billed per output second; long clips
  are slow and expensive. Trim first with `video-clip-extractor`.
- **Deprecation watch**: `gen4_aleph` is scheduled to deactivate **2026-07-31** in favour
  of Aleph 2.0 — if a job 404s on the model, switch the `MODEL` constant / model string.

## Recipes

### 1. Runway Gen-4 Aleph — restyle/relight one clip (recommended)

The bundled helper submits to `POST /v1/video_to_video`, pins API version
`2024-11-06`, then polls `GET /v1/tasks/{id}` every 5 s until `SUCCEEDED`.

```bash
export RUNWAYML_API_SECRET=key_xxx

# Relight a plate to golden hour, keep the camera move
python3 scripts/runway_v2v.py \
  --video https://cdn.example.com/plate.mp4 \
  --prompt "relight as warm golden-hour sunset, soft rim light, long shadows" \
  --ratio 1280:720 --out golden.mp4

# Restyle to anime with a style-reference image + fixed seed
python3 scripts/runway_v2v.py \
  --video ./ad_cut.mp4 \
  --prompt "restyle as hand-drawn 2D anime, bold linework, cel shading" \
  --reference https://cdn.example.com/style_ref.png \
  --seed 42 --out ad_anime.mp4
```

Prompt patterns that work well with Aleph:
- **Relight**: "relight as {golden hour | overcast | neon night | studio key light}".
- **Season/weather**: "change to winter, snow on the ground, bare trees".
- **Restyle**: "restyle as {claymation | oil painting | 90s VHS | brand teal-and-orange palette}".
- **Object edit**: "remove the parked car"; "add a small fairy riding on the raccoon".
- **Angle**: "same scene, low-angle wide shot" (Aleph can predict a new camera angle).

Valid `--ratio` values: `1280:720 720:1280 1104:832 960:960 832:1104 1584:672 848:480 640:480`.

### 2. Same model via Replicate (simplest auth)

```bash
export REPLICATE_API_TOKEN=r8_xxx
pip install replicate  # or use the REST API directly
```
```python
import replicate
out = replicate.run(
    "runwayml/gen4-aleph",
    input={
        "video": "https://cdn.example.com/plate.mp4",
        "prompt": "restyle as claymation, soft studio light",
        "aspect_ratio": "16:9",           # Replicate uses w:h ratio labels
        # "reference_image": "https://.../ref.png",
        # "seed": 42,
    },
)
print(out)  # URL(s) to the rendered MP4
```

### 3. AI/ML API (curl)

```bash
curl -s -X POST https://api.aimlapi.com/v2/video/generations \
  -H "Authorization: Bearer $AIMLAPI_KEY" -H "Content-Type: application/json" \
  -d '{"model":"runway/gen4_aleph",
       "video_url":"https://cdn.example.com/plate.mp4",
       "prompt":"night scene, cool moonlight, neon signs"}'
# → {"id":"...","status":"queued"}   then poll:
curl -s -H "Authorization: Bearer $AIMLAPI_KEY" \
  "https://api.aimlapi.com/v2/video/generations?generation_id=<id>"
```

### 4. Alibaba Wan 2.6 v2v (best for live-action ↔ anime, native audio)

Wan 2.6's v2v mode restyles footage and adds synchronized audio / lip-sync. Access it
through a provider (WaveSpeed `alibaba/wan-2.6`, Atlas Cloud, or DashScope). The request
shape mirrors the others: a `video_url` + `prompt`, submit → poll → download. Prefer the
**Flash** variant for cheap iteration, the standard variant for the final render.

### 5. Batch restyle

```bash
for f in clips/*.mp4; do
  python3 scripts/runway_v2v.py --video "$f" \
    --prompt "restyle in our brand look: teal + coral, clean flat lighting" \
    --out "out/$(basename "$f")"
  sleep 2   # be gentle on rate limits
done
```

## Verify

- `python3 -c "import py_compile; py_compile.compile('scripts/runway_v2v.py', doraise=True)"`
  compiles clean; `python3 scripts/runway_v2v.py --help` prints usage with no key set.
- A real run prints `task id: <id>`, streams `status=RUNNING …`, then writes the MP4 and
  echoes its path. Confirm the output opens and that **motion/timing matches the source**
  while only the look changed — that is the signal v2v (not generation) actually ran.
- Sanity-check length/fps with `ffprobe out.mp4` (see `ffmpeg-cookbook`); Aleph output
  duration tracks the input clip.
- Re-running with the **same `--seed`** should give a near-identical result — use it to
  A/B prompt tweaks without reroll noise.

## Pitfalls

- **Input must be reachable.** A `file://` or private path fails on Runway/AI-ML; give a
  public HTTPS URL or let the helper inline a local file as a data URI (keep it small).
- **v2v ≠ generation.** If the output ignores the source motion, you're on a t2v/i2v
  endpoint — verify you hit `/v1/video_to_video` (Aleph), not image/text-to-video.
- **Prompt the *change*, not the whole scene.** Describe the delta ("relight as night",
  "remove the sign") — over-describing the existing content fights the structural anchor.
- **Cost creeps with length.** Billing is per output second; trim to the beats you need
  before submitting. A 30 s clip is 6× the cost of a 5 s hero moment.
- **Poll politely.** Runway throttles faster than 5 s/poll and wastes credits — the helper
  already waits 5 s. Don't tighten it.
- **Model sunset.** `gen4_aleph` deactivates 2026-07-31; a sudden model 404 means migrate
  to Aleph 2.0 (update `MODEL` / the model string).
- **Content moderation.** Faces of real people, logos, and likeness edits can be rejected;
  a `FAILED` status with a moderation message means rework the prompt/source, not a bug.
- **Rights.** Only transform footage you have the rights to; AI restyle doesn't launder
  licensing, talent, or music clearances for client work.
