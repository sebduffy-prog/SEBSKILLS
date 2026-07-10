---
name: sfx-foley-generation
category: media
description: >
  Generate sound effects and foley from a TEXT prompt — footsteps, whooshes, impacts, UI
  clicks, ambience, stingers — via ElevenLabs SFX v2 (cloud, up to 30s, seamless loop, 48kHz)
  or Meta AudioGen (local, free, no key). Also derive SFX for a VIDEO by describing its
  shots then generating per-cut sounds. Use when someone says "make a sound effect",
  "generate foley", "text to SFX", "add sound to this clip", "sound design for my ad",
  "whoosh/impact/riser", "ambient bed", "SFX for animation", or "AudioGen". Produces WAV/MP3
  SFX ready to place on a timeline.
when_to_use:
  - Create a named sound effect from a description (door creak, laser, coin pickup, rain ambience)
  - Sound-design an ad/animation/UGC edit — whooshes on cuts, impacts on logo hits, risers into reveals
  - Generate a seamless looping ambience or texture bed (rain, café, engine idle, drone)
  - Derive foley for a silent video by describing each shot and generating matching SFX per cut
  - Batch many prompts into a small SFX library for a project, cheaply and repeatably
  - Need a fully local, no-API-key SFX generator (AudioGen) when the clip can't leave the machine
when_not_to_use:
  - Generating spoken words / narration / a voice → voice-clone-tts
  - Isolating or removing existing sounds/vocals from a recording → stem-separation
  - Only mixing, ducking music under VO, or loudness-normalising finished audio → audio-loudness-ducking
  - Converting/trimming/concatenating audio files with no generation → ffmpeg-cookbook
  - Cleaning up / denoising a real recording rather than synthesising a new sound → audio-loudness-ducking (or Adobe media_enhance_speech)
keywords: [sfx, sound effects, foley, text to sound, text-to-audio, elevenlabs, sound-generation, audiogen, audiocraft, sound design, whoosh, impact, riser, ambience, loop, sound for video, generative audio, 48khz]
similar_to: [voice-clone-tts, stem-separation, audio-loudness-ducking, ffmpeg-cookbook, media-toolchain-bootstrap]
inputs_needed:
  - A clear sound description per effect (material + action + space, e.g. "heavy wooden door slams shut, small room reverb")
  - Engine choice — ElevenLabs SFX v2 (cloud, needs ELEVENLABS_API_KEY) or AudioGen (local, free)
  - Per-effect duration and whether it should seamlessly loop
  - For video foley — the clip and its cut/shot list (timecodes + what each shot shows)
produces: One or more WAV/MP3 sound-effect files (48kHz from ElevenLabs, 16kHz from AudioGen) ready to place on an edit timeline
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# SFX / Foley Generation

Turn a text prompt into a **sound effect** — footstep, whoosh, impact, UI blip, riser, or a
looping ambience bed. Two engines: **ElevenLabs SFX v2** (cloud, best quality, 48kHz, up to
30s, seamless loops) and **Meta AudioGen** (local, free, no key, 16kHz). Output is a
WAV/MP3 you drop onto a timeline.

## When to use

You need a specific sound that you'd otherwise hunt for in a stock library — and you want it
shaped exactly to the brief (right material, action, space, length). Also for **sound design
passes** on an ad or animation: whooshes on transitions, impacts on logo hits, a riser into
the reveal. If you need someone to *speak*, that's `voice-clone-tts`, not this.

## Prerequisites (this Mac)

- **ElevenLabs (recommended)** — an API key in `ELEVENLABS_API_KEY`. The helper uses only
  Python stdlib (`urllib`), so **no SDK install needed**. SFX generation is billed per
  request/duration on your ElevenLabs plan. Model id: `eleven_text_to_sound_v2`.
- **AudioGen (local, free)** — `pip install audiocraft torch torchaudio`. It needs
  **Python ≥3.9** but the wheels are heavy and Apple-Silicon MPS support is partial; first
  run downloads `facebook/audiogen-medium` (~3GB). Export `PYTORCH_ENABLE_MPS_FALLBACK=1`;
  if MPS ops crash, force CPU. Output is **16kHz mono** — fine for texture, not for a hero
  hit. Use it only when audio can't leave the machine or you want zero cloud spend.
- **ffmpeg** (trim/convert/place, and to pull frames for video foley) — no brew here, use the
  portable binary: `FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")`.
- Helper: `scripts/gen_sfx.py` (ElevenLabs SFX → file, stdlib-only, validates ranges).

## Write a prompt that actually sounds right

The single biggest quality lever. Name **material + action + space**, and imply dynamics:

- Weak: `door` → Strong: `heavy oak door slams shut, echoing stone corridor`
- Weak: `whoosh` → Strong: `fast cinematic whoosh transition, low sub swell, short`
- Weak: `rain` → Strong: `steady rain on a tin roof, distant thunder, seamless ambience`

Percussive one-shots (impacts, clicks, coin pickups) want a **short** duration; ambiences and
risers want length + shape. `prompt_influence` trades literalness (high, ~0.6) vs creative
variation (low, ~0.2); default 0.3.

## Recipe A — one SFX via ElevenLabs (the helper)

```bash
export ELEVENLABS_API_KEY=sk_...
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")

# a punchy impact (short, literal)
python3 scripts/gen_sfx.py "deep cinematic boom impact, sub-bass tail" hit.mp3 \
  --duration 2 --influence 0.6 --format mp3_44100_128

# a seamless ambience loop
python3 scripts/gen_sfx.py "cosy café ambience, murmur, cups, espresso machine" cafe.mp3 \
  --duration 22 --loop
```

Duration must be **0.5–30s**; omit `--duration` to let the model pick. `--loop` makes the
clip repeat with no perceptible seam (great for beds you'll extend under a scene). The helper
writes raw audio bytes and refuses a suspiciously tiny response (a silent-fail guard).

## Recipe B — the same call in your own code (no SDK)

```python
import os, json, urllib.request
req = urllib.request.Request(
    "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128",
    data=json.dumps({"text": "retro 8-bit coin pickup blip",
                     "model_id": "eleven_text_to_sound_v2",
                     "duration_seconds": 1, "prompt_influence": 0.5,
                     "loop": False}).encode(),
    headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"],
             "Content-Type": "application/json"}, method="POST")
open("coin.mp3", "wb").write(urllib.request.urlopen(req).read())
```

Official SDK equivalent (if you'd rather `pip install elevenlabs`):
`ElevenLabs().text_to_sound_effects.convert(text=..., model_id="eleven_text_to_sound_v2", duration_seconds=1, prompt_influence=0.5, loop=False)` → an audio byte stream.

## Recipe C — batch a project SFX library

Drive many prompts from a file, one MP3 each:

```bash
# sfx.txt: one "name|prompt|duration" per line
while IFS='|' read -r name prompt dur; do
  python3 scripts/gen_sfx.py "$prompt" "sfx/${name}.mp3" --duration "$dur"
done < sfx.txt
```

Keep prompts and durations versioned alongside the edit so the library regenerates identically.

## Recipe D — foley for a silent video (describe → generate → place)

ElevenLabs' "Video-to-Sound" is an app-UI feature that watches frames; programmatically you
reproduce it by **describing the shots, then generating per-cut SFX**:

1. Get the cut list — timecodes + what each shot shows. (Use `shot-scene-detection` to find
   cut points, or pull frames: `"$FF" -i clip.mp4 -vf fps=1 frames/%03d.jpg` and read them.)
2. Turn each shot into a material+action+space prompt and generate with Recipe A, sizing
   `--duration` to that shot's length.
3. Place each SFX at its cut timecode over the video:

```bash
"$FF" -i clip.mp4 -i whoosh.mp3 -i impact.mp3 \
  -filter_complex "[1]adelay=1200|1200[a1];[2]adelay=3400|3400[a2];\
                   [a1][a2]amix=inputs=2[sfx]" \
  -map 0:v -map "[sfx]" -c:v copy -shortest out.mp4
```

`adelay=<ms>|<ms>` offsets each SFX to its cut (per channel). For a full mix with a music
bed and VO ducking, hand the stems to `audio-loudness-ducking`.

## Recipe E — fully local with AudioGen (no key)

```python
import os
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
from audiocraft.models import AudioGen
from audiocraft.data.audio import audio_write
m = AudioGen.get_pretrained("facebook/audiogen-medium")   # ~3GB first run
m.set_generation_params(duration=5)                        # seconds
wav = m.generate(["dog barking", "emergency siren passing"])
for i, w in enumerate(wav):
    audio_write(f"sfx_{i}", w.cpu(), m.sample_rate,        # -> sfx_0.wav, 16kHz
                strategy="loudness", loudness_compressor=True)
```

Local, free, no watermark, but **16kHz** and no seamless-loop mode — treat it as a fallback
or a bulk texture source, not a 48kHz hero effect.

## Finish the audio

Loudness-normalise and place/convert with ffmpeg:

```bash
"$FF" -i hit.mp3 -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:a libmp3lame -q:a 2 hit_norm.mp3
# extend a 22s loop to fill a 60s scene:
"$FF" -stream_loop -1 -i cafe.mp3 -t 60 -c copy cafe_60s.mp3
```

## Verify

- `"$FF" -i hit.mp3` → duration ≈ what you asked and sample rate is 44.1/48k (ElevenLabs) or
  16k (AudioGen). A ~0-length or <1KB file means the request errored — the helper already
  guards this and prints the HTTP error body.
- **Listen.** Does it match material + action + space? Percussive one-shots should be tight,
  not smeared; ambiences should sit under, not compete. Regenerate with a sharper prompt or a
  higher `--influence` if it drifts.
- Loop test: play a `--loop` clip end-to-start (`-stream_loop`) and confirm no click/seam.

## Pitfalls

- **Vague prompt → generic mush.** Add material, action, and acoustic space; state "short" for
  one-shots. This matters more than any parameter.
- **`duration_seconds` out of range** → must be **0.5–30**; omit it to auto-size. Longer than
  30s only exists via `--loop` + ffmpeg `-stream_loop`.
- **401/422 from ElevenLabs** → missing/invalid `ELEVENLABS_API_KEY`, or a bad param. The
  helper prints the API's error body — read it; don't retry blindly.
- **AudioGen install/MPS pain** → heavy wheels, partial Apple-Silicon support. Export
  `PYTORCH_ENABLE_MPS_FALLBACK=1`; if it still crashes, force CPU (slow). Its 16kHz output is
  the tell you used the local path.
- **Expecting "video-to-sound" as a one-shot API** → the auto-from-frames feature is in the
  ElevenLabs app UI; do it programmatically via Recipe D (describe shots → per-cut SFX).
- **Licensing/usage** → confirm your ElevenLabs plan's rights before shipping generated SFX in
  a paid client deliverable. AudioGen output is CC-BY-NC (research) — check terms for commercial ads.
- **Wrong skill** → need *words* spoken? That's `voice-clone-tts`. Removing an existing sound?
  `stem-separation`. Only mixing/ducking? `audio-loudness-ducking`.
