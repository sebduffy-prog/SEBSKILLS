---
name: voice-clone-tts
category: media
description: >
  Generate spoken narration and voiceover LOCALLY — few-shot voice cloning from a ~10s
  reference clip (Chatterbox / GPT-SoVITS) or fast preset-voice TTS (Kokoro), served either
  as raw Python or a drop-in OpenAI-compatible /v1/audio/speech endpoint. Use when someone
  says "clone this voice", "make a voiceover", "narrate this script", "text to speech",
  "TTS locally", "AI voice from a sample", "read this in my voice", "generate a VO", or
  "local alternative to ElevenLabs/OpenAI TTS". Produces a WAV/MP3 in the target voice, no cloud.
when_to_use:
  - Clone a specific person's voice from a short sample to record a VO line or narration
  - Generate long-form narration from a script locally, no per-character cloud billing
  - Stand up an OpenAI-compatible TTS endpoint so existing OpenAI-SDK code just points at localhost
  - Need a fast, lightweight preset narrator voice (audiobook, explainer) without cloning anyone
  - Produce multilingual VO (French/Spanish/etc.) in a cloned or preset voice
when_not_to_use:
  - Only need to TRANSCRIBE speech to text → use whisper-caption-burn or youtube-transcript-lift
  - Want on-screen captions burned into a video → whisper-caption-burn
  - Need to isolate/remove vocals or split stems from a song → stem-separation
  - Cleaning up / denoising an existing recording, not synthesizing → audio-loudness-ducking (or Adobe media_enhance_speech)
  - Converting/normalizing an audio file's format only → ffmpeg-cookbook
  - Ducking music under a finished VO → audio-loudness-ducking
keywords: [tts, text to speech, voice clone, voice cloning, voiceover, VO, narration, chatterbox, kokoro, gpt-sovist, gpt-sovits, few-shot, zero-shot, openai compatible, /v1/audio/speech, elevenlabs alternative, speech synthesis, neural voice, local tts, kokoro-fastapi]
similar_to: [whisper-caption-burn, stem-separation, audio-loudness-ducking, ffmpeg-cookbook, media-toolchain-bootstrap]
inputs_needed:
  - The script/text to speak (and target language if not English)
  - For cloning — a clean ~10s reference clip of the target voice AND confirmation you have consent/rights to clone it
  - Voice choice — clone a specific voice (Chatterbox/GPT-SoVITS) or a preset narrator (Kokoro)
  - Delivery — a WAV/MP3 file, or a running OpenAI-compatible endpoint
produces: A narration WAV/MP3 in the chosen (cloned or preset) voice, optionally via a local OpenAI-compatible TTS server
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Voice Clone TTS

Turn a script into spoken audio **locally**: **clone** a voice from ~10s of reference
(Chatterbox, or GPT-SoVITS for the highest few-shot fidelity), or use a fast **preset**
narrator (Kokoro). Deliver a WAV/MP3, or a drop-in **OpenAI-compatible** endpoint so any
`base_url`-swappable OpenAI-SDK code keeps working with zero cloud spend.

## When to use

You need a voiceover, narration, or a specific person's voice reading a line — and you'd
rather not pay ElevenLabs/OpenAI per character or ship the audio to a cloud. If you only
need speech → text, stop: that's `whisper-caption-burn`.

> **Consent gate.** Cloning a real person's voice needs their permission and a lawful use.
> Every Chatterbox output also carries Resemble's imperceptible **Perth watermark** (near-100%
> detection, survives MP3) — you cannot pass it off as an unmarked human recording. Confirm
> rights before you generate.

## Pick an engine

| Engine | Clone? | Strengths | License | On this Mac |
|--------|--------|-----------|---------|-------------|
| **Chatterbox** | Yes (zero-shot, ~10s ref) | Best all-round clone, 23 langs, emotion `exaggeration` | MIT | Python **3.11** venv, `device="mps"` |
| **Kokoro** | No (preset voices) | Tiny (82M), fast, clean narrators | Apache-2.0 | any Python, `PYTORCH_ENABLE_MPS_FALLBACK=1` |
| **GPT-SoVITS** | Yes (few-shot, ~1min ref) | Highest-fidelity clone + fine-tune, built-in WebUI/API | MIT | heavier; run its own repo/venv |

Default to **Chatterbox** for cloning a VO, **Kokoro** when any pleasant narrator will do.

## Prerequisites (this Mac)

- **Python 3.11 for Chatterbox** — the system Python here is 3.9 and Chatterbox needs ≥3.11.
  Make an isolated venv: `python3.11 -m venv ~/.venvs/tts && source ~/.venvs/tts/bin/activate`
  then `pip install chatterbox-tts torch torchaudio`. (Kokoro is happy on any 3.9+.)
- **Apple Silicon** — Chatterbox runs on `device="mps"`. For Kokoro export
  `PYTORCH_ENABLE_MPS_FALLBACK=1` so unimplemented MPS ops fall back to CPU instead of crashing.
  No CUDA on this Mac — expect near-real-time on MPS, several× slower on pure CPU.
- **ffmpeg** (prep the reference clip, WAV→MP3) — no brew here, use the portable binary:
  `FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")`
  (also at `_research_bank/bin`).
- **Docker** (only for the OpenAI-compatible server recipe) — the Kokoro-FastAPI / chatterbox-tts-api
  images are the fastest way to a `/v1/audio/speech` endpoint.
- Helper: `scripts/clone_vo.py` (Chatterbox clone with script chunking → one WAV).

## Recipe A — prep a clean reference clip

Cloning quality lives or dies on the reference. Give it **~10s of clean, single-speaker,
no-music** speech at the model's rate (Chatterbox is happy with 24 kHz mono):

```bash
"$FF" -ss 00:00:05 -t 10 -i source.mov \
  -af "highpass=f=80,lowpass=f=8000,afftdn=nf=-25,loudnorm=I=-18" \
  -ac 1 -ar 24000 ref10s.wav
```

Trim to a stretch with **no background music, no overlap, natural pace**. Longer isn't
better — a pristine 8–12s beats a noisy 40s. (Music under the voice? Isolate it first with
`stem-separation`, then trim.)

## Recipe B — clone a VO with Chatterbox (local)

One-off line, straight Python:

```python
import torchaudio
from chatterbox.tts import ChatterboxTTS
m = ChatterboxTTS.from_pretrained(device="mps")            # "cpu" if MPS misbehaves
wav = m.generate("Welcome back to the show.",
                 audio_prompt_path="ref10s.wav",
                 exaggeration=0.5, cfg_weight=0.5)          # ↑exaggeration=more dramatic
torchaudio.save("line.wav", wav.reshape(1, -1), m.sr)      # m.sr is the true sample rate
```

Full script → single narration WAV (chunks long text so it stays coherent):

```bash
source ~/.venvs/tts/bin/activate
python3 scripts/clone_vo.py --ref ref10s.wav --in script.txt --out vo.wav \
  --exaggeration 0.6 --cfg 0.4 --device mps
# multilingual clone (23 langs): add  --lang fr   (uses ChatterboxMultilingualTTS)
```

Tuning: `exaggeration` 0.5 neutral → 0.7+ theatrical; drop `cfg_weight` to ~0.3 for a
faster, looser delivery. Regenerate a chunk if a word slurs — output varies per run.

## Recipe C — preset narrator with Kokoro (no clone, fast)

```python
import soundfile as sf, numpy as np
from kokoro import KPipeline
pipe = KPipeline(lang_code="a")                    # a=US, b=UK, e=ES, f=FR, i=IT, j=JP, p=PT-BR, z=ZH
chunks = [audio for _, _, audio in pipe(open("script.txt").read(), voice="af_heart")]
sf.write("narration.wav", np.concatenate(chunks), 24000)   # Kokoro is always 24 kHz
```

Kokoro **cannot clone** — pick a preset voice (e.g. `af_heart`, `af_bella`, `am_michael`,
`bf_emma`). You can blend two: `voice="af_sky+af_bella"`. Great for explainers/audiobooks
where identity doesn't matter and you want it instant.

## Recipe D — OpenAI-compatible endpoint (drop-in)

Point existing OpenAI-SDK code at localhost instead of OpenAI — same request shape.

```bash
# Kokoro (preset voices) — CPU image
docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest

# Chatterbox (voice cloning) — repo: travisvn/chatterbox-tts-api (docker-compose in repo)
#   exposes /v1/audio/speech AND /v1/audio/voices for uploaded reference voices
```

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8880/v1", api_key="not-needed")
client.audio.speech.create(model="kokoro", voice="af_sky",
                           input="Piped straight through the OpenAI SDK.",
                           response_format="mp3").stream_to_file("out.mp3")
```

Or raw curl: `curl http://localhost:8880/v1/audio/speech -H 'Content-Type: application/json'
-d '{"model":"kokoro","voice":"af_sky","input":"Hello.","response_format":"wav"}' -o out.wav`.
Kokoro-FastAPI also returns per-word timestamps — handy if you'll caption with `whisper-caption-burn`.

## Recipe E — highest-fidelity clone (GPT-SoVITS)

When Chatterbox isn't close enough, `RVC-Boss/GPT-SoVITS` does few-shot from ~1 min of
reference and supports fine-tuning for a near-perfect match. Clone its repo, run its own
venv + WebUI (`python webui.py`) or the built-in API server; it's heavier, so keep it in a
separate environment from the Chatterbox venv. Reach for it only when the extra fidelity is
worth the setup.

## Finish the audio

Loudness-normalize for delivery and convert to MP3:

```bash
"$FF" -i vo.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:a libmp3lame -q:a 2 vo.mp3
```

To sit the VO over music, hand off to `audio-loudness-ducking`.

## Verify

- `"$FF" -i vo.wav` → confirm duration is sane and sample rate matches the engine
  (Chatterbox `m.sr`, Kokoro 24000). A 0.1s file means generation errored silently.
- **Listen.** Check the clone actually resembles the reference and no chunk slurs/clips.
  Regenerate offending chunks (output is stochastic).
- Server recipe: `curl -s localhost:8880/v1/audio/voices` (or `/health`) lists voices — a
  200 with voices means the endpoint is live before you wire in the SDK.

## Pitfalls

- **`chatterbox-tts` won't install** → you're on Python 3.9 (system default). Use the 3.11 venv.
- **MPS crash / "op not implemented"** → for Kokoro export `PYTORCH_ENABLE_MPS_FALLBACK=1`;
  for Chatterbox fall back to `device="cpu"` (slower but reliable).
- **Robotic / off clone** → the reference is noisy, has music, or is multi-speaker. Re-cut a
  clean single-speaker 10s (Recipe A). More reference ≠ better; cleaner is.
- **Long text drifts or truncates** → generate per sentence/paragraph and concatenate (the
  helper does this). Don't feed a whole page in one `generate` call.
- **Sample-rate mismatch** → always save with the model's real rate (`m.sr`, or 24000 for
  Kokoro). Hardcoding 44100 pitch-shifts the voice.
- **Expecting Kokoro to clone** → it can't; it's preset-voice only. Use Chatterbox/GPT-SoVITS.
- **Watermark / consent** → Chatterbox embeds Perth watermark and cloning needs the person's
  permission. Don't clone a voice you have no rights to.
