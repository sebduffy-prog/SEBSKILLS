---
name: reel-foundry
category: recipes
description: >-
  Recreate a Wan2.2 / FramePack-style automated ad-reel factory as a named combo — take a prompt list
  or a pile of supplied footage and turn it into a captioned, correctly-ducked, platform-sized vertical
  reel with almost no manual editing. Chain video-gen-pipeline (or your own clips) → shot-scene-detection
  → social-video-reframe → whisper-caption-burn → audio-loudness-ducking → ffmpeg-cookbook to assemble.
  Reach for this for a TikTok/Reels/Shorts ad, a product teaser, or a batch of variant cuts you want
  reproducible in code instead of a timeline editor.
when_to_use:
  - You want a Wan2.2/FramePack-style hands-off ad-reel factory that goes from prompts-or-footage to a finished vertical cut
  - You have supplied footage (or generated clips) and need it auto-segmented, reframed to 9:16, captioned and mixed
  - You need burned-in captions plus music-under-voice ducking without opening Premiere/CapCut
  - You want to batch out several platform sizes or copy variants from one source reproducibly
  - You need a repeatable pipeline (detect → reframe → caption → duck → assemble) rather than manual edits
when_not_to_use:
  - You only need to generate raw AI clips from prompts — use video-gen-pipeline alone
  - You only need to reframe one horizontal video to 9:16 — use social-video-reframe alone
  - You only need to burn captions onto an existing cut — use whisper-caption-burn alone
  - You only need to duck music under a voiceover — use audio-loudness-ducking alone
  - You just want to trim/concat/normalise existing files — use ffmpeg-cookbook alone
keywords: [wan2.2, framepack, ad reel, automated reel, faceless video, tiktok, reels, shorts, vertical video, auto caption, ducking, reframe, shot detection, ffmpeg, batch video, combo]
similar_to: [video-gen-pipeline, shot-scene-detection, social-video-reframe, whisper-caption-burn, audio-loudness-ducking, ffmpeg-cookbook]
inputs_needed: >-
  Either a shot-prompt list (for generation) OR a folder of supplied source clips; a target platform/aspect
  (9:16 TikTok/Reels/Shorts, 1:1, etc.); an optional music bed and/or voiceover track; caption styling
  (font, size, position). For the generative path only: a fal.ai key + rented GPU/API budget.
produces: >-
  One (or a batch of) finished platform-sized reel MP4(s) — reframed to the target aspect, with burned-in
  captions and music ducked under speech — plus the intermediate per-shot clips and an SRT/caption file.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Reel Foundry

## What it recreates

A local, code-driven stand-in for **Wan2.2** / **FramePack** "automated ad-reel"
factories — the class of tools that take a brief (or a pile of raw footage) and
spit out a finished, captioned, platform-ready vertical reel with no timeline
editing. Those products bundle generation, auto-editing, reframing, captioning
and mixing behind one button. This recipe reassembles that same button from six
sibling skills you already have, so the whole pipeline is inspectable and
re-runnable instead of a black box.

## Feasibility

**Amber.** Everything except net-new motion generation is fully reproducible
locally with ffmpeg + whisper and needs no external service:

- **Green** for the footage-based path — if you *supply* clips, every step
  (segment → reframe → caption → duck → assemble) runs on your machine, offline,
  deterministically. Treat this as the default and it is a solid green.
- **Amber** for exactly one step: generating brand-new motion frames from
  prompts via `video-gen-pipeline` calls out to the fal.ai queue (Veo / Kling /
  Wan / Seedance) or a rented GPU. That step needs a key, credits and network.
  It is the *only* part that is not local.

Do not oversell this as "one-click Wan2.2". It reproduces the *pipeline*
honestly; the generative spark in the amber step is still a hosted model, not
something running on your laptop. Skip that step entirely (bring your own
footage) and the whole thing goes green.

## The combo

An ordered chain — each step is a real sibling skill in `skills/media/`:

1. **video-gen-pipeline** *(AMBER — skip if you have footage)* — turn a shot-prompt
   list into per-shot MP4 clips via the fal.ai queue (Veo 3.1 / Kling / Wan /
   Seedance), submit→poll→download each shot. If you already have source clips,
   skip this step and start at step 2.
2. **shot-scene-detection** — run PySceneDetect over the source (generated or
   supplied) to find cut points, so long takes get split into clean shots you can
   reorder and trim to beat.
3. **social-video-reframe** — reframe each shot from landscape to the target
   aspect (9:16 / 1:1) with subject-aware cropping so faces/action stay in frame.
4. **whisper-caption-burn** — transcribe speech with whisper, generate an SRT,
   and burn styled captions into the picture (faceless-reel style).
5. **audio-loudness-ducking** — sidechain-duck the music bed under the voiceover
   and normalise to platform loudness (about -14 LUFS) so speech stays intelligible.
6. **ffmpeg-cookbook** — concat the reframed, captioned, ducked shots into one
   continuous timeline, normalise fps/codec/size, and export the final deliverable.

## Prerequisites

- ffmpeg + ffprobe on PATH (see `media-toolchain-bootstrap` if missing).
- whisper (or faster-whisper) available for the caption step.
- PySceneDetect installed for shot detection.
- **Amber step only:** a `FAL_KEY` env var and API credit, plus network access.
  Not needed on the footage-only path.
- A working directory with your source clips and/or prompt list, an optional
  music bed, and an optional voiceover track.

## Run it

Do the steps in order; each is its own skill invocation so you can stop, inspect
intermediates, and re-run any single stage.

1. **Get shots.** Either invoke `video-gen-pipeline` with your prompt list to
   generate per-shot clips (amber), **or** drop your supplied clips into
   `work/shots/` and jump to step 2.
2. **Segment.** Run `shot-scene-detection` on any long source to split it into
   discrete shots; collect all shots into `work/shots/`.
3. **Reframe.** For each shot, run `social-video-reframe` to the chosen aspect
   (e.g. 1080x1920 for 9:16). Write results to `work/reframed/`.
4. **Caption.** Run `whisper-caption-burn` over the voiceover (or the clips' own
   audio) to produce `captions.srt`, then burn styled captions onto each
   reframed shot into `work/captioned/`.
5. **Mix.** Run `audio-loudness-ducking` to sidechain the music under the voice
   and normalise loudness; produce the final mixed audio track (or per-shot audio).
6. **Assemble.** Use `ffmpeg-cookbook` to concat `work/captioned/*` with the
   mixed audio, normalise fps/codec/pixel format, and export `reel_final.mp4`.
7. **Batch (optional).** To produce multiple platform sizes or copy variants,
   loop steps 3–6 with different aspect/caption params over the same step-2 shots.

## Verify

- `ffprobe reel_final.mp4` — confirm resolution matches the target aspect
  (e.g. 1080x1920), fps and codec are consistent, and audio + video streams are
  both present and the same duration.
- Play the reel: captions are legible, in sync, and inside the safe area; music
  audibly drops when the voice speaks (the ducking worked).
- Check integrated loudness (`ffmpeg ... -af ebur128` or `loudnorm` print) sits
  near the platform target (~-14 LUFS) with no clipping.
- Watch the cut points: shots from `shot-scene-detection` land on clean frames,
  no mid-word chops, no black flashes at concat seams.
- Amber path only: each generated shot downloaded fully before segmentation —
  a truncated fal download will silently shorten the reel.

## Pitfalls

- **Do not oversell the amber step.** Say plainly that generation is a hosted
  model behind an API key; the "local reel factory" claim only holds for the
  footage path.
- **Aspect/scale drift.** Mixing sources of different resolutions before the
  concat causes ffmpeg to letterbox or stretch. Reframe *every* shot to the exact
  same WxH in step 3 before assembly.
- **fps mismatch at concat.** Clips at 24/25/30 fps concatenated without
  normalising will judder or desync audio. Force a single fps in the
  `ffmpeg-cookbook` assemble step.
- **Captions burned before reframe.** Burn captions *after* reframing (step 4
  follows step 3) or the crop will slice your text off. Keep the order.
- **Ducking with no speech track.** `audio-loudness-ducking` needs a voice
  sidechain; if the reel is music-only, skip step 5 rather than ducking against
  silence.
- **Whisper on music-heavy audio.** Loud beds degrade transcription — caption
  from a clean voiceover stem where possible, not the final mix.
- **Re-running the whole chain to fix one shot** wastes the amber budget. Fix the
  single stage and re-assemble from cached intermediates.
