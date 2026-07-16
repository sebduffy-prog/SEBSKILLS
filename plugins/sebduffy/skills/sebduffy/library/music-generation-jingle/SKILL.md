---
name: music-generation-jingle
category: media
description: >
  Generate original music, jingles, stings, loops, and underscores from a text
  prompt using open models (MusicGen / AudioCraft, Stable Audio Open, ACE-Step)
  or hosted APIs (Replicate, Suno-via-provider). Use to produce a 5-15s brand
  jingle, a 30s ad bed, a looping background track, or a scratch scratch demo
  score — with the licensing homework done so the output is actually clearable
  for a client campaign. Covers prompt craft, duration/loop control, and the
  commercial-vs-non-commercial trap that bites agencies.
when_to_use:
  - Need a bespoke jingle, sting, logo mnemonic, or short brand audio idiom for an ad
  - Want a royalty-free-style background bed or loop under a video/social edit
  - Prototyping a scratch score or mood reference before briefing a real composer
  - Generating multiple musical directions fast to test with a client or in a pitch
  - Deciding which music model/API is safe to use for paid commercial work
  - Producing an instrumental or vocal track programmatically at scale via API
when_not_to_use:
  - You need to separate vocals/drums from an existing song — use stem-separation
  - You need speech / voiceover / narration, not music — use voice-clone-tts
  - You only need loudness normalization or ducking on existing audio — use audio-loudness-ducking
  - You want to build the wider video the music sits under — use video-gen-pipeline
keywords:
  - music generation
  - jingle
  - musicgen
  - audiocraft
  - stable audio
  - ace-step
  - suno
  - text-to-music
  - background music
  - loop
  - sound logo
  - ad music
  - replicate
  - royalty free
  - licensing
  - score
similar_to:
  - voice-clone-tts
  - stem-separation
  - audio-loudness-ducking
  - video-gen-pipeline
inputs_needed: >
  A text description of the music (genre, mood, instrumentation, BPM, reference
  vibe), target duration, and whether the output will be used commercially. For
  hosted paths, a REPLICATE_API_TOKEN or provider key. For local paths, Python
  3.9+ and ideally a GPU (CPU works for MusicGen-small, slowly).
produces: >
  One or more audio files (.wav / .mp3) of generated music at the requested
  length, plus a clear licensing verdict on whether the chosen model's output
  is usable for the intended commercial or non-commercial purpose.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Music & Jingle Generation

Turn a text brief into original music — a 10s jingle, a 30s ad bed, a loopable
underscore — using open-source models or hosted APIs, and know which outputs you
can actually clear for a paying client.

## When to use

Reach for this when you need *new* music from a description: a brand sting for a
social edit, a scratch score for an animatic, or a batch of mood directions for a
pitch. If you're touching existing recordings (separating, normalising, ducking)
this is the wrong skill — see the alternatives above.

## Prerequisites

- **Python 3.9+** and `ffmpeg` for the local paths. On this Mac, `python3` is 3.9
  and there is no GPU — MusicGen-small runs on CPU (tens of seconds per clip);
  Stable Audio Open and ACE-Step really want a CUDA GPU, so prefer hosting them.
- **A GPU or a hosted API** for anything beyond quick MusicGen-small tests. The
  fastest reliable route for agency work is Replicate (`pip install replicate`,
  `export REPLICATE_API_TOKEN=...`).
- **Licensing awareness before you start** — this is the part that bites. See the
  table below; do NOT ship a client campaign without confirming the output is
  clearable.

## Licensing (READ FIRST — the agency trap)

| Model | Code license | **Weights / output usable commercially?** |
|-------|--------------|-------------------------------------------|
| MusicGen (Meta AudioCraft) | MIT (code) | **NO — weights are CC-BY-NC 4.0. Non-commercial only.** Fine for internal scratch/mood refs, NOT a paid deliverable. |
| Stable Audio Open 1.0 | Stability AI Community License | Free for non-commercial + for orgs under \$1M/yr revenue; above that needs an Enterprise license. VCCP-scale clients ⇒ check the enterprise threshold. |
| ACE-Step v1 (3.5B) | **Apache 2.0** | **Yes — permissive, commercial use allowed.** Best open choice for clearable deliverables. |
| Suno (via third-party provider) | proprietary | Governed by Suno's own terms + the reseller's; there is no official public Suno API. Treat legal status as unsettled — get sign-off. |

Rule of thumb: **prototype with MusicGen, deliver with ACE-Step (Apache-2.0) or a
licensed/enterprise path.** When in doubt, the safe deliverable is a real library
track or a briefed composer.

## Recipes

### 1. Fastest quality — MusicGen via Replicate (prototype / mood refs)

```bash
pip install replicate
export REPLICATE_API_TOKEN=r8_xxx
```

```python
import replicate, urllib.request
out = replicate.run(
    "meta/musicgen",
    input={
        "prompt": "warm optimistic acoustic guitar and hand-claps, "
                  "uplifting brand jingle, 120 BPM, bright and clean",
        "duration": 12,               # seconds
        "model_version": "stereo-large",
        "output_format": "mp3",
        "normalization_strategy": "loudness",
    },
)
urllib.request.urlretrieve(str(out), "jingle_v1.mp3")
```

`meta/musicgen` accepts a `continuation`/`input_audio` melody prompt too. Output is
CC-BY-NC — keep it internal.

### 2. Fully local, no key — MusicGen-small on CPU (AudioCraft)

```bash
python3 -m pip install -U audiocraft   # pulls torch; heavy, one-time
```

```python
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write

model = MusicGen.get_pretrained('facebook/musicgen-small')   # small|medium|large|melody
model.set_generation_params(duration=10)                     # seconds
wavs = model.generate([
    'minimal corporate underscore, soft piano and pads, hopeful, 90 BPM',
    'punchy retro synth sting, 3 second logo mnemonic, confident',
])
for i, wav in enumerate(wavs):
    # writes take_{i}.wav, EBU-loudness normalized
    audio_write(f'take_{i}', wav.cpu(), model.sample_rate,
                strategy="loudness", loudness_compressor=True)
```

Melody-conditioned: use `facebook/musicgen-melody` and pass a reference tune via
`model.generate_with_chroma(...)`.

### 3. Clearable deliverable — ACE-Step (Apache-2.0, GPU)

```bash
pip install git+https://github.com/ace-step/ACE-Step.git
acestep --port 7865 --bf16 true        # launches Gradio UI (text-to-music, lyrics, edit, extend)
```

ACE-Step (`ACE-Step/ACE-Step-v1-3.5B` on HuggingFace) does ~4 min of audio in
~20s on an A100, supports lyrics + multiple languages + voice cloning, and is
Apache-2.0 — so its output is the safest open path for a paid campaign. Run it on
a rented GPU (Replicate/Runpod/Colab) rather than this CPU-only Mac.

### 4. Stable Audio Open — SFX and short loops (GPU)

Best for one-shots, risers, and drum/tech loops (weak at vocals). 44.1kHz stereo,
up to ~47s:

```python
from stable_audio_tools import get_pretrained_model
from stable_audio_tools.inference.generation import generate_diffusion_cond
model, cfg = get_pretrained_model("stabilityai/stable-audio-open-1.0")
audio = generate_diffusion_cond(
    model, steps=100, cfg_scale=7,
    conditioning=[{"prompt": "128 BPM tech house drum loop",
                   "seconds_start": 0, "seconds_total": 30}],
    sampler_type="dpmpp-3m-sde",
)
```

### 5. Suno via a third-party provider (vocals / full songs)

No official public API exists. Providers (e.g. `docs.sunoapi.org`, apiframe) wrap
account pools behind a REST endpoint. Pattern is always: POST a prompt → poll a
job id → download. Legally unsettled — only use with explicit client/legal
sign-off, never as the default for a deliverable.

## Prompt craft for jingles

- Name **genre + mood + instrumentation + tempo**: "upbeat indie-pop, jangly
  guitar, tambourine, 128 BPM, feel-good".
- Say the **role**: "3-second sound logo", "15-second radio bed with a button
  ending", "loopable 30s underscore, no drums".
- Add **negatives via absence** — say "no vocals", "sparse", "minimal" rather than
  listing what to avoid; these models don't take hard negative prompts.
- **Generate 4-8 takes**, don't polish one prompt. Cheap to fan out, then curate.

## Post-production

- **Loop cleanly**: generate longer than needed, then trim to a zero-crossing bar
  boundary in an editor or `ffmpeg -ss/-t`.
- **Fit to picture / duck under VO**: hand off to `audio-loudness-ducking`.
- **Normalise** to -14 LUFS (social) or -23 LUFS (broadcast) — MusicGen's
  `strategy="loudness"` gets you close; verify with `ffmpeg -af loudnorm=print_format=json`.

## Verify

- **File is real audio**: `ffprobe -v error -show_entries format=duration,bit_rate,format_name jingle_v1.mp3`
- **Length matches the brief** (within a beat) and there's no abrupt cutoff.
- **Licence check done**: confirm the model's output class (table above) matches
  the intended use before it leaves the building.
- **Listen on phone speaker** — jingles live on tiny speakers; check the hook cuts
  through and the ending has a clean button.

## Pitfalls

- **Shipping CC-BY-NC output as a paid deliverable.** MusicGen weights are
  non-commercial. This is the #1 mistake — prototype with it, deliver with ACE-Step
  or a licensed track.
- **Assuming Suno has an official API.** It doesn't; every route is third-party and
  legally grey. Don't build a client pipeline on it without sign-off.
- **Trying to run ACE-Step / Stable Audio locally on this Mac.** CPU-only + Python
  3.9 will crawl or fail — host the GPU models; keep only MusicGen-small local.
- **Over-long prompts.** These models ignore paragraphs. One dense sentence of
  genre/mood/instrument/tempo beats a wall of adjectives.
- **Expecting realistic lead vocals** from MusicGen/Stable Audio — they don't do
  it well. Use ACE-Step (lyrics support) or a provider for sung vocals.
- **No loudness/format normalisation.** Raw model output varies wildly in level;
  always normalise before delivery.
