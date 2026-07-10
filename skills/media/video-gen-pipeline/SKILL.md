---
name: video-gen-pipeline
category: media
description: >
  Generate short AI video clips from text (or a first-frame image) with the current model catalogue —
  Veo 3.1, Kling 2.1/3.0 Pro, Seedance 2.0, Wan, Sora 2 — via the fal.ai queue API, then stitch the shots
  into one continuous multi-shot cut with ffmpeg concat. Use when someone says "generate a short ad from
  prompts", "make an AI video", "text-to-video", "turn these prompts into a 20-second video", "stitch my
  AI clips into one video", "kling / veo / seedance / wan clip", "image-to-video from this frame", or
  "prompt list to a finished cut". Covers submit→poll→download per shot, chaining last-frame→next-shot,
  and concat/normalise into a single deliverable.
when_to_use:
  - Turn a list of shot prompts into a finished short film / ad by generating each clip then stitching them
  - Generate one text-to-video clip (Veo 3.1, Kling, Seedance 2.0, Wan) and download the mp4
  - Image-to-video — animate a still (Flux/Nano-Banana output, product shot, storyboard frame) into motion
  - Chain shots for continuity — feed the last frame of clip N as the first frame of clip N+1
  - Concat several already-generated AI clips into one video with matching size/fps/codec
  - Build a rough animatic/ad from a storyboard where each panel becomes a generated shot
when_not_to_use:
  - You only need to join/trim/normalise existing (non-AI) footage → use ffmpeg-cookbook
  - You want a still image from a prompt, not a moving clip → use flux-image-gen or nano-banana-image
  - You need a node-graph local pipeline with custom nodes/LoRAs (AnimateDiff/Wan locally) → use comfyui-workflow-runner
  - You have one long video to slice into vertical clips for socials → use long-video-to-shorts or social-video-reframe
  - You want smoother slow-mo / higher fps on real footage, not generation → use frame-interpolation-retiming
keywords: [text-to-video, image-to-video, ai video, veo 3, veo 3.1, kling, kling 2.1, seedance, seedance 2.0, wan, sora, fal.ai, fal queue, generative video, short ad, multi-shot, stitch clips, ffmpeg concat, storyboard to video, animatic, shot list, i2v, t2v]
similar_to: [ffmpeg-cookbook, flux-image-gen, nano-banana-image, comfyui-workflow-runner, long-video-to-shorts, frame-interpolation-retiming]
inputs_needed:
  - The shot prompts (an ordered list) — or the input images for image-to-video
  - A FAL_KEY (fal.ai) — or another provider key if you prefer; which model/tier to use
  - Target aspect ratio (16:9 / 9:16), duration per shot, resolution (720p/1080p), and total length
  - Whether shots must be continuous (chain last-frame→next) or are independent cuts
produces: A single stitched .mp4 built from AI-generated shots (plus each raw shot clip)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Video Gen Pipeline (text/image → clips → one stitched cut)

Two stages:
1. **Generate** each shot — text-to-video or image-to-video — via a hosted model. All the big models
   live behind one API shape on **fal.ai**; only the endpoint id and a couple of input fields change.
2. **Stitch** the downloaded clips into one continuous cut with **ffmpeg concat**, normalising size/fps/codec.

The hosted API is **async (a queue)**: POST the prompt, get a `status_url`, poll until `COMPLETED`, then
GET the `response_url` for the signed video URL and download it. `scripts/gen_clip.py` does all three
with only the Python stdlib (no SDK, no pip install).

## When to use

You have prompts (or storyboard frames) and want moving clips, or you already have AI clips and want them
joined into one deliverable. For non-AI editing, stills, or local node-graph pipelines, use the siblings
in `when_not_to_use`.

## Prerequisites (this Mac)

- **A fal.ai key**: create one at fal.ai/dashboard/keys, then `export FAL_KEY=...`. Auth header is
  **`Authorization: Key $FAL_KEY`** (not Bearer). Generation is billed per second of output — check the
  model's price before batch runs.
- **ffmpeg** for stitching. No brew here — use the portable binary:
  ```bash
  FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")  # pip install imageio-ffmpeg
  # or the copy at _research_bank/bin/ffmpeg
  ```
- `python3` (stdlib only) to run the helper — no extra packages.

### Model endpoints (fal, 2026)

| Model | Endpoint id | Notes |
|---|---|---|
| Veo 3.1 (Google) | `fal-ai/veo3.1` | 720p/1080p/4K, 16:9 & 9:16, native audio (`generate_audio`) |
| Kling 2.1 Pro | `fal-ai/kling-video/v2.1/pro/text-to-video` | strong camera/motion control |
| Kling 3.0 Pro | `fal-ai/kling-video/v3/pro/text-to-video` | multi-shot, native audio |
| Seedance 2.0 | `fal-ai/bytedance/seedance-2.0/text-to-video` | multimodal, audio-synced; `/fast/` variant is cheaper |
| Wan 2.7 | `fal-ai/wan/v2.7/text-to-video` | fast, budget catalogue |

For image-to-video, most models expose a sibling endpoint (e.g.
`fal-ai/kling-video/v2.1/pro/image-to-video`) — pass `image_url` in the input. Field names vary a little
per model (`duration` is `"8s"` on Veo, `"5"` on Kling); check the model's API tab if a field is rejected.

## Recipe A — prompt list → stitched cut

**1. Generate each shot.** One call per prompt; download to `shotN.mp4`.

```bash
S=skills/media/video-gen-pipeline/scripts/gen_clip.py
python3 $S --endpoint fal-ai/veo3.1 --out shot1.mp4 \
  --input '{"prompt":"wide aerial over a foggy coastline at dawn, cinematic","aspect_ratio":"16:9","duration":"8s","resolution":"1080p"}'
python3 $S --endpoint fal-ai/veo3.1 --out shot2.mp4 \
  --input '{"prompt":"low tracking shot of waves crashing on black rocks, slow motion","aspect_ratio":"16:9","duration":"8s","resolution":"1080p"}'
python3 $S --endpoint fal-ai/veo3.1 --out shot3.mp4 \
  --input '{"prompt":"close on a lighthouse lamp igniting, warm glow, golden hour","aspect_ratio":"16:9","duration":"8s","resolution":"1080p"}'
```

Keep **aspect_ratio and resolution identical across shots** so the concat is clean.

**2. Stitch with ffmpeg concat.** Re-encoding filter-concat is the safe path — it normalises fps, SAR
and codec even when the clips differ slightly:

```bash
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -i shot1.mp4 -i shot2.mp4 -i shot3.mp4 -filter_complex \
  "[0:v]scale=1920:1080,setsar=1,fps=24[v0]; \
   [1:v]scale=1920:1080,setsar=1,fps=24[v1]; \
   [2:v]scale=1920:1080,setsar=1,fps=24[v2]; \
   [v0][0:a][v1][1:a][v2][2:a]concat=n=3:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac final.mp4
```

If any clip has **no audio track**, drop the `a=1` streams: use `concat=n=3:v=1:a=0[v]`, `-map "[v]"`,
and no `-c:a`. To lay a music bed over silent clips instead, add `-i music.m4a` and map that.

**Faster, no re-encode** (only when every clip is byte-compatible — same codec/res/fps, which fal Veo
output usually is):

```bash
printf "file '%s'\n" shot1.mp4 shot2.mp4 shot3.mp4 > list.txt
"$FF" -f concat -safe 0 -i list.txt -c copy final.mp4
```

## Recipe B — image-to-video (animate a still)

Give the model a first frame (a Flux/Nano-Banana image, a product photo, a storyboard panel). fal reads
a URL, so upload the image somewhere reachable, or pass a `data:` URI if the model accepts it:

```bash
python3 $S --endpoint fal-ai/kling-video/v2.1/pro/image-to-video --out shot1.mp4 \
  --input '{"prompt":"slow push-in, gentle parallax, subtle wind","image_url":"https://example.com/frame.jpg","duration":"5"}'
```

## Recipe C — continuity (chain last frame → next shot)

For a shot that continues seamlessly, pull the **last frame** of clip N and feed it as the first frame of
clip N+1 (image-to-video):

```bash
"$FF" -sseof -0.1 -i shot1.mp4 -frames:v 1 -q:v 2 shot1_last.jpg   # grab final frame
# upload shot1_last.jpg, then use its URL as image_url for the next image-to-video call
```

Continuity is best-effort — model drift means it won't be pixel-perfect. Cut on motion or add a quick
cross-dissolve at the seam (`xfade`) to hide the join.

## Verify

- Each raw shot: `"$FF" -i shotN.mp4 -hide_banner` prints duration, resolution and stream layout — confirm
  it matches what you asked for (length, 1920x1080, has/lacks audio).
- Stitched file: total duration ≈ sum of shots; play it — `open final.mp4`.
- Programmatic length check:
  ```bash
  python3 -c "import imageio_ffmpeg,subprocess as s; ff=imageio_ffmpeg.get_ffmpeg_exe(); print(s.run([ff,'-i','final.mp4'],capture_output=True,text=True).stderr.split('Duration:')[1][:11])"
  ```

## Pitfalls

- **Mismatched clips = broken concat.** Different resolution/fps/SAR is the #1 failure. Generate every
  shot at the same aspect_ratio + resolution, and always run the filter-concat (Recipe A step 2) which
  re-normalises. Reserve `-c copy` for clips you've confirmed are identical.
- **Audio present on some clips, absent on others** makes `-c copy` concat drop or desync audio. Either
  make every clip have audio, or strip audio from all and add one music bed.
- **Field names differ per model.** `duration` is `"8s"` on Veo but `"5"` (seconds as string/int) on Kling;
  `resolution`/`aspect_ratio` aren't universal. If the API 4xx's on a field, open the model's API tab and
  match its exact schema — the helper prints the server's error body.
- **Cost + time.** Each 1080p 8s shot can take 1–5 min and costs real money; a 5-shot ad is 5 billed jobs.
  Prototype at 720p / the `/fast/` variants, then re-run finals.
- **Signed URLs expire.** fal's result URL is short-lived; the helper downloads immediately — don't stash
  the URL for later.
- **Endpoints churn.** Model ids get versioned and deprecated (Veo 3 → 3.1, Kling 2.1 → 3.0). If an
  endpoint returns "no longer supported", check fal.ai/models for the current id.
