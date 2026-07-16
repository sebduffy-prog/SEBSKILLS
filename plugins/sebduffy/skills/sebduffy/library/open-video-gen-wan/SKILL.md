---
name: open-video-gen-wan
category: media
description: >
  Self-host open-weight text-to-video and image-to-video on your OWN GPU with license-clean models —
  Wan 2.2 (MoE A14B + the 24GB-friendly TI2V-5B), HunyuanVideo 13B, LTX-Video — not a SaaS API. Trigger
  on "run Wan 2.2 locally", "self-hosted text-to-video", "open-weight T2V/I2V", "generate video on my own
  GPU / a rented A100", "HunyuanVideo setup", "LTX-Video inference", "no per-clip API fees", "on-prem AI
  video", or "which open video model is safe for UK commercial use". Covers GPU/VRAM sizing, exact
  clone+download+generate commands, and the Apache-2.0 vs Tencent-licence trap.
when_to_use:
  - Generate T2V or I2V clips on a self-hosted / rented GPU with weights you control, no per-clip SaaS fee
  - Stand up Wan 2.2 (T2V-A14B, I2V-A14B, or the 24GB TI2V-5B) end to end on a cloud GPU box
  - Run HunyuanVideo 13B or LTX-Video inference and pick the right model for the VRAM you can rent
  - Choose a commercially SAFE open video model for UK/EU client work (Apache-2.0 vs restricted licences)
  - Keep footage/prompts on-prem for confidential brand or unreleased-product work
  - Batch-generate many clips cheaply on one owned GPU rather than paying a hosted queue per second
when_not_to_use:
  - You just want a clip fast from a hosted API and don't care about self-hosting → use video-gen-pipeline
  - You want to restyle EXISTING footage keeping its motion (v2v) → use controllable-video-to-video
  - You need a node-graph UI with LoRAs/custom nodes rather than CLI → use comfyui-workflow-runner
  - You only have an Apple-Silicon Mac and no CUDA GPU to rent → use video-gen-pipeline (these need NVIDIA)
  - You want a still image from a prompt, not motion → use flux-image-gen or nano-banana-image
keywords: [wan 2.2, wan2.2, hunyuanvideo, ltx-video, ltxv, open-weight video, text-to-video, image-to-video, self-hosted, t2v, i2v, moe a14b, ti2v-5b, apache-2.0, on-prem, cuda gpu, generate.py, offload_model]
similar_to: [video-gen-pipeline, controllable-video-to-video, comfyui-workflow-runner, flux-image-gen]
inputs_needed:
  - A CUDA (NVIDIA) GPU — owned or rented (RunPod/Lambda/Vast). Apple-Silicon Macs cannot run these.
  - Enough VRAM for the chosen model (24GB for Wan TI2V-5B; 45-80GB for A14B / Hunyuan)
  - The prompt (T2V) or a first-frame image (I2V); target resolution and clip length
  - Where the finished mp4 lands and how you'll pull it back (scp / rsync)
produces:
  - An mp4 clip generated locally from open weights, plus the exact reproducible generate command
  - A model + licence recommendation matched to your VRAM budget and client jurisdiction
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Open-Weight Video Generation (Wan 2.2 / HunyuanVideo / LTX-Video)

Run text-to-video (T2V) and image-to-video (I2V) on a GPU **you** control, from **open weights** — no
per-clip SaaS bill, prompts and footage stay on-prem, and you pick a licence that's clean for client work.

## When to use

Reach for this over `video-gen-pipeline` when the point is *self-hosting*: cost control at volume,
confidentiality (unreleased product, embargoed campaign), or needing weights on your own infra. If you
just want a clip and don't care where it runs, the hosted `video-gen-pipeline` skill is faster.

## Prerequisites (be honest about the hardware)

- **An NVIDIA CUDA GPU. This does NOT run on your Mac.** Apple-Silicon MPS is not supported by these
  repos. On this Mac you *drive* a remote box (RunPod / Lambda / Vast.ai / a client's server), you don't
  generate locally. Everything below runs **on that GPU box** over SSH.
- VRAM by model (single-GPU minimums, verified from the repos):

  | Model | Repo (HuggingFace) | Params | Min VRAM | Notes |
  |-------|--------------------|--------|----------|-------|
  | **Wan2.2-TI2V-5B** | `Wan-AI/Wan2.2-TI2V-5B` | 5B dense | **~24GB (RTX 4090)** | best value; 720p T+I2V |
  | Wan2.2-T2V-A14B | `Wan-AI/Wan2.2-T2V-A14B` | 14B MoE | ~80GB | 480P + 720P text-to-video |
  | Wan2.2-I2V-A14B | `Wan-AI/Wan2.2-I2V-A14B` | 14B MoE | ~80GB | 480P + 720P image-to-video |
  | HunyuanVideo | `tencent/HunyuanVideo` | 13B | 45-60GB (80GB rec.) | 129 frames @ 720p |
  | LTX-Video 13B | `Lightricks/LTX-Video` | 13B | consumer-GPU w/ distilled/FP8 | fast; 1216×704 @ 30fps |

- Python 3.10+ **on the GPU box**, a recent CUDA/PyTorch, `git`, and `huggingface-cli`
  (`pip install "huggingface_hub[cli]"`). Log in with `huggingface-cli login` if a repo gates downloads.

### Licence trap — read before client work

- **Wan 2.2 → Apache-2.0.** Clean for commercial + UK/EU. Default pick for VCCP client deliverables.
- **LTX-Video → Apache-2.0** (core weights; some checkpoints add OpenRAIL-M). Also clean.
- **HunyuanVideo → Tencent Hunyuan Community License, NOT Apache.** Critically, that licence **does not
  apply in the EU, the UK, or South Korea**, forbids using outputs to train competing models, and needs a
  separate grant above 100M MAU. **For a UK agency, treat Hunyuan as research/eval only** and ship on Wan
  or LTX. Always confirm the current `LICENSE.txt` before delivery.

## Recipes (run on the GPU box)

### A. Wan 2.2 TI2V-5B — the 24GB starting point

```bash
# 1. Clone + install (on the GPU box)
git clone https://github.com/Wan-Video/Wan2.2.git && cd Wan2.2
pip install -r requirements.txt

# 2. Download weights (~fits a single 24GB card)
huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./Wan2.2-TI2V-5B

# 3a. Text-to-video (720p). --offload_model + --t5_cpu keep it inside 24GB.
python generate.py --task ti2v-5B --size '1280*704' --ckpt_dir ./Wan2.2-TI2V-5B \
  --offload_model True --convert_model_dtype --t5_cpu \
  --prompt "A slow dolly across a rain-slicked neon Tokyo alley at night, cinematic, 35mm"

# 3b. Image-to-video from a first frame
python generate.py --task ti2v-5B --size '1280*704' --ckpt_dir ./Wan2.2-TI2V-5B \
  --offload_model True --convert_model_dtype --t5_cpu \
  --image ./first_frame.jpg \
  --prompt "the product rotates slowly on a turntable, soft studio light"
```

Note the quoting: `--size '1280*704'` (the `*` must be quoted in bash). Output mp4 lands in the repo dir.

### B. Wan 2.2 A14B (MoE) — higher quality, needs ~80GB

```bash
huggingface-cli download Wan-AI/Wan2.2-T2V-A14B --local-dir ./Wan2.2-T2V-A14B

# Single 80GB GPU
python generate.py --task t2v-A14B --size '1280*720' --ckpt_dir ./Wan2.2-T2V-A14B \
  --offload_model True --convert_model_dtype \
  --prompt "Two boxers spar in a sunlit gym, dust in the light, slow motion"

# 8-GPU node (much faster) — FSDP + sequence parallel
torchrun --nproc_per_node=8 generate.py --task t2v-A14B --size '1280*720' \
  --ckpt_dir ./Wan2.2-T2V-A14B --dit_fsdp --t5_fsdp --ulysses_size 8 \
  --prompt "Your prompt here"
```

I2V is identical with `--task i2v-A14B`, `--ckpt_dir ./Wan2.2-I2V-A14B`, and `--image path.jpg`.

### C. HunyuanVideo 13B (eval only for UK/EU — see licence trap)

```bash
git clone https://github.com/Tencent-Hunyuan/HunyuanVideo && cd HunyuanVideo
python -m pip install -r requirements.txt
huggingface-cli download tencent/HunyuanVideo --local-dir ./ckpts

python3 sample_video.py \
  --video-size 720 1280 --video-length 129 --infer-steps 50 \
  --prompt "A cat walks on the grass, realistic style." \
  --flow-reverse --use-cpu-offload --save-path ./results
```

`--video-length` must be `4k+1` frames (129 = ~5s @ ~24fps). `--use-cpu-offload` trades speed for VRAM.

### D. LTX-Video — fastest, consumer-GPU friendly, Apache-2.0

```bash
git clone https://github.com/Lightricks/LTX-Video && cd LTX-Video
pip install -e '.[inference]'

# Image-to-video with the distilled 13B config (weights auto-pull on first run)
python inference.py \
  --prompt "waves crash against dark rocks, moody overcast dawn" \
  --conditioning_media_paths ./first_frame.jpg --conditioning_start_frames 0 \
  --height 704 --width 1216 --num_frames 121 --seed 42 \
  --pipeline_config configs/ltxv-13b-0.9.8-distilled.yaml
```

Drop `--conditioning_media_paths`/`--conditioning_start_frames` for pure text-to-video. The distilled and
FP8 configs are the ones that fit smaller cards — use those before the full 13B.

### E. Pull the result back to your Mac

```bash
# from your Mac
scp user@gpu-box:/path/to/Wan2.2/output.mp4 ~/Desktop/
# or keep a whole results dir in sync
rsync -avz user@gpu-box:/path/to/results/ ~/Desktop/openvid/
```

## Verify

- `nvidia-smi` on the box shows the GPU and enough free VRAM **before** you launch.
- Dry-run the model choice against your budget:
  `python3 -c "vram=24; print('TI2V-5B' if vram<45 else ('Hunyuan/A14B' if vram>=45 else 'LTX-distilled'))"`
- After a run, confirm the file is real motion, not a stalled 0-byte:
  `ffprobe -v error -show_entries stream=codec_type,nb_frames,width,height -of default=noprint_wrappers=1 output.mp4`
- `nb_frames` should match your requested length (129 for Hunyuan default, 121 for the LTX example above).

## Pitfalls

- **Do not attempt to run on the Mac.** No CUDA → these repos fall over. Rent a GPU; drive it over SSH.
- **HunyuanVideo licence excludes UK/EU/South Korea.** For VCCP client deliverables ship on **Wan 2.2 or
  LTX-Video (Apache-2.0)**; keep Hunyuan to internal R&D. Re-read `LICENSE.txt` each time — terms move.
- **OOM on A14B / Hunyuan** → add/keep `--offload_model True --convert_model_dtype` (Wan) or
  `--use-cpu-offload` (Hunyuan), drop to 480P, or pick TI2V-5B / LTX-distilled instead of the 14B MoE.
- **`--size '1280*720'` unquoted** → bash treats `*` as a glob and the arg breaks. Always quote it.
- **First run is slow**: it downloads tens of GB of weights. Do it once to a persistent volume, not an
  ephemeral pod disk you lose on restart.
- **Clip length ≠ arbitrary.** Hunyuan wants `4n+1` frames; Wan/LTX have config-fixed defaults. Don't
  hand-set odd lengths and expect them to work — start from the repo's example numbers.
- **Weights are open, generated content still needs clearance** — brand/likeness/trademark rights aren't
  waived by an Apache licence on the model. Clear the *output* like any other asset.
