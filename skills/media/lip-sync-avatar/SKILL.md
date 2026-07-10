---
name: lip-sync-avatar
category: media
description: >
  Make a face TALK — drive lips on a photo or video clip from any audio/VO so a
  spokesperson, presenter, or dubbed actor mouths the words. Use when someone says
  "lip sync", "talking head", "talking avatar", "make this photo speak", "AI presenter",
  "visual dubbing", "sync the mouth to this voiceover", "MuseTalk / Wav2Lip / LatentSync",
  or "HeyGen-style avatar". Routes between self-hosted open models on a cloud GPU
  (MuseTalk / Wav2Lip / LatentSync), a one-call Replicate run, or a managed avatar API.
  Produces an MP4 with mouth motion matched to the audio.
when_to_use:
  - Drive the mouth on an existing headshot or presenter clip from a recorded/AI voiceover
  - Visual-dubbing a video into another language so lips match the new-language audio track
  - Spin up a talking-head "AI spokesperson" from a photo + a script-read VO
  - Batch-generate many short talking clips (product lines, personalised names) from one face
  - Pick the right engine for a quality/cost/hardware budget (Wav2Lip fast vs LatentSync/MuseTalk sharp)
when_not_to_use:
  - You need to GENERATE the voice/VO first → voice-clone-tts, then feed its WAV here
  - You need a full text-to-video scene (no fixed face) → video-gen-pipeline
  - You only need burned-in captions/subtitles on a video → whisper-caption-burn
  - You just need to swap/composite a face image (no speech) → background-removal-batch or an image tool
  - You want to clean/denoise the driving audio only → audio-loudness-ducking
keywords: [lip sync, lipsync, talking head, talking avatar, musetalk, wav2lip, latentsync, sadtalker, visual dubbing, dubbing, ai presenter, ai spokesperson, heygen, sync.so, replicate, face animation, mouth sync, talking photo]
similar_to: [voice-clone-tts, video-gen-pipeline, whisper-caption-burn, media-toolchain-bootstrap, video-audio-rip]
inputs_needed:
  - A driving face — a headshot image OR a short video clip of one clearly-visible, front-facing face
  - The audio to sync to — a WAV/MP3 VO (generate it first with voice-clone-tts if you don't have one)
  - A route decision — self-host on a rented GPU, one-call Replicate, or a managed avatar API (needs an API key)
  - Consent confirmation — you have the right to make THIS face say THIS audio
produces: An MP4 of the face with lip/mouth motion synced to the supplied audio track
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Lip-Sync Avatar

Take a **face** (photo or clip) plus **audio** and produce a video where the mouth moves
in time with the speech — a talking head, an AI spokesperson, or a visually-dubbed actor.

## When to use

You have a face and a voiceover and you want them married so it looks like the person is
saying it. If you don't have the VO yet, make it first with `voice-clone-tts`, then come
back here. If there's no fixed face and you want a whole generated scene, that's
`video-gen-pipeline`, not this.

> **Consent gate (read first).** Putting words in a real person's mouth is a deepfake.
> Only sync a face you have the rights to, with audio that person (or your client) has
> authorised. Don't impersonate public figures or make anyone appear to say things they
> didn't. Keep a record of the consent. For client/brand work, label synthetic presenters
> where required.

## Reality on this Mac

Every strong open lip-sync model (MuseTalk, Wav2Lip, LatentSync, SadTalker) needs an
**NVIDIA CUDA GPU** — MuseTalk targets CUDA 11.7/11.8 + torch 2.0.1, and this machine has
no CUDA and ships Python 3.9. So you have three honest routes:

| Route | What runs it | Best when |
|-------|--------------|-----------|
| **A — Managed API** (`sync.so`, HeyGen) | their cloud, you send URLs | fastest, no GPU, highest polish, per-video billing, brand/agency work |
| **B — One-call Replicate** | a rented GPU behind one API call | you want an open model (LatentSync/Wav2Lip) without owning a GPU, pennies/run |
| **C — Self-host** (MuseTalk/Wav2Lip) | a GPU box you rent (Colab, RunPod, Lambda) | batch volume, no per-video fee, full control, offline/private data |

Pick by constraint: **A** for polish and zero setup, **B** for cheap open-model runs,
**C** for volume or privacy. All three still need your face + audio prepped locally first.

## Prerequisites

- **A driving face.** A **static photo** (Wav2Lip/SadTalker/MuseTalk accept a still) or a
  **short video** of a front-facing, well-lit, single face with the mouth visible.
  LatentSync and MuseTalk want a **video** input for the most natural result.
- **The audio**, as WAV or MP3 (`voice-clone-tts` output is ideal). Clean, single-speaker.
- **ffmpeg** to prep clips locally (no brew here — use the portable binary):
  `FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")`
- **Route A/B keys** — `SYNC_API_KEY` / `HEYGEN_API_KEY`, or `REPLICATE_API_TOKEN`.
  Never hardcode; export in the shell. `pip install replicate` for route B.
- Helper: `scripts/lipsync_replicate.py` (route B — uploads local files, runs, downloads).

## Prep the inputs (all routes)

Get the face clip and audio into clean, matched formats — most failures are bad inputs:

```bash
# Face video → 25fps, sane size, front-facing crop already done. No spaces in filenames.
"$FF" -i presenter_raw.mov -r 25 -vf "scale=-2:720" -an face.mp4
# Audio → 16kHz mono WAV (Wav2Lip is happiest at 16k; APIs accept mp3/wav)
"$FF" -i vo.mp3 -ac 1 -ar 16000 vo.wav
```

If the face isn't cleanly framed, crop to a tight head-and-shoulders first — off-centre or
tiny faces are the #1 cause of a mushy mouth.

## Route A — managed API (sync.so, fastest polish)

`sync.so` runs `lipsync-2` / `lipsync-2-pro` — the current best-in-class hosted model.
It takes **URLs** (host your `face.mp4` and `vo.wav` somewhere reachable, e.g. an S3 /
Google Drive direct link, or their upload endpoint), then polls to done:

```bash
curl -s -X POST https://api.sync.so/v2/generate \
  -H "x-api-key: $SYNC_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "model": "lipsync-2",
    "input": [
      {"type": "video", "url": "https://.../face.mp4"},
      {"type": "audio", "url": "https://.../vo.wav"}
    ],
    "options": {"sync_mode": "loop"}
  }'
# → returns {"id": "...", "status": "PENDING"}; poll GET /v2/generate/{id} until COMPLETED,
#   then download the outputUrl.
```

`sync_mode: "loop"` (or `bounce`) reuses the base clip when audio is longer than video.
Route A also covers **HeyGen** when you want a fully-synthetic stock/custom avatar rather
than your own footage — `POST https://api.heygen.com/v2/video/generate` with header
`X-Api-Key`, a `video_inputs[].character` (`avatar_id` or `talking_photo_id`) and a
`voice` block (`type:"audio"` + `audio_url`, or `type:"text"` + `input_text` + `voice_id`).

## Route B — one Replicate call (open models, cheap)

No GPU, no server — one API call rents one. Good models (pass a local file, it uploads):

| Replicate model | Input | Note |
|-----------------|-------|------|
| `bytedance/latentsync` | video + audio | diffusion, sharpest; ~$0.09/run on L40S (~90s) |
| `devxpy/cog-wav2lip` | face (img/vid) + audio | fastest/cheapest, accepts a **still**, softer teeth |
| `cjwbw/sadtalker` | single image + audio | animates a photo with head motion (experimental) |

```python
import replicate  # export REPLICATE_API_TOKEN first
out = replicate.run(
    "bytedance/latentsync",
    input={"video": open("face.mp4", "rb"), "audio": open("vo.wav", "rb")},
)
print(out)   # URL to the finished mp4
```

Or just run the helper, which picks the model, uploads your local files, and downloads
the result next to them:

```bash
pip install replicate
python3 scripts/lipsync_replicate.py --face face.mp4 --audio vo.wav \
  --model latentsync --out talking.mp4
# --model wav2lip  (accepts a still image for --face; add --pads "0 20 0 0" to catch the chin)
```

## Route C — self-host MuseTalk on a rented GPU

For batch/volume or private data, run the open model yourself on a CUDA box (Colab T4+,
RunPod, Lambda). MuseTalk is MIT-licensed and real-time capable (30+fps). On the GPU host:

```bash
conda create -n MuseTalk python==3.10 -y && conda activate MuseTalk
pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 \
  --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
pip install -U openmim && mim install mmengine "mmcv==2.0.1" "mmdet==3.1.0" "mmpose==1.1.0"
sh ./download_weights.sh            # pulls MuseTalk, sd-vae, whisper, dwpose, etc. into ./models
```

Point `configs/inference/test.yaml` at your `video_path` + `audio_path`, then:

```bash
export FFMPEG_PATH=/path/to/ffmpeg      # a static ffmpeg build
sh inference.sh v1.5 normal             # v1.5 weights, batch mode → results/
sh inference.sh v1.5 realtime           # low-latency mode for streaming/live avatars
```

Result MP4s land in `results/`. **Wav2Lip** self-host is lighter (runs on a modest GPU) if
you only need a still-photo talker; **LatentSync** self-host is heaviest (RTX 4090-class).

## Finish the video

Mux clean audio back and (optionally) upscale, since lip-sync models often output a soft
face region:

```bash
# Replace the model's re-encoded audio with your pristine VO, keep the synced video
"$FF" -i talking.mp4 -i vo.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest final.mp4
```

For a crisper face, hand `final.mp4` to `ai-upscale-restore`. To burn captions, `whisper-caption-burn`.

## Verify

- **Watch it at 100% and 0.5×.** The mouth must open on plosives (b/p/m) and close on
  silence. Drift that grows over the clip = audio/video frame-rate mismatch (re-export the
  face at 25fps).
- `"$FF" -i final.mp4` → audio and video **durations match** and there's an audio stream.
  A silent output means the mux dropped the track (check `-map`).
- **Face region sharpness** — mush/smearing around the mouth means the face was too small or
  off-centre; re-crop tighter and re-run. Wav2Lip is softest; switch to LatentSync/MuseTalk
  if teeth/detail matter.
- Route A/B: confirm the job reached `COMPLETED`/`succeeded` before downloading — a failed
  job can still return a JSON body with no usable URL.

## Pitfalls

- **No CUDA here.** You cannot run these locally on this Mac. Use route A or B, or rent a
  GPU for C. Don't waste time `pip install`-ing MuseTalk on Python 3.9.
- **Blurry / smeared mouth** → the face is too small, off-centre, or turned away. Crop to a
  front-facing head-and-shoulders and re-run. This fixes most quality complaints.
- **Mouth drifts out of sync over time** → face video and audio are at different frame
  rates. Force the face to 25fps (`-r 25`) and mono 16k audio, then re-run.
- **Wav2Lip looks soft / bad teeth** → it's the fastest but lowest-fidelity model. Move to
  `bytedance/latentsync` (route B) or MuseTalk (route C) for a sharp mouth.
- **Managed API "can't fetch input"** → the `url` must be publicly reachable (a Drive
  *view* link isn't a direct file; use a direct/download URL or the API's own upload).
- **Spaces in filenames** break several Replicate models and the sync API — keep paths
  space-free.
- **Audio longer than a short base clip** → set `sync_mode: loop`/`bounce` (route A) or use
  a longer face video; a 3s clip under a 30s VO will stutter or freeze.
- **Consent.** Don't sync a face you don't have rights to. This is deepfake tech — treat it
  like it.
