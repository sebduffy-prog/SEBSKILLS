---
name: neural-net-from-scratch
category: ml
description: >
  Write your own PyTorch training loop from bare metal — Dataset/DataLoader, forward/backward,
  mixed-precision (AMP), gradient accumulation, LR warmup+cosine, grad clipping, checkpoint
  save/resume, and a diagnostic playbook for loss=NaN / not-learning / OOM bugs. Includes a
  minimal ~130-line GPT (nanoGPT-shaped) you can actually train on your own text. Use when
  someone says "training loop", "train a model in PyTorch", "loss is NaN", "model won't learn",
  "build a transformer/GPT from scratch", or "AMP / checkpointing".
when_to_use:
  - Hand-writing a PyTorch training loop instead of using a Trainer (Lightning/HF Trainer)
  - Debugging loss=NaN, loss stuck flat, exploding/vanishing gradients, or CUDA OOM
  - Building a minimal GPT / MLP / CNN from scratch to understand forward+backward
  - Adding mixed precision (AMP), gradient accumulation, or LR scheduling by hand
  - Implementing checkpoint save + exact resume (model + optimizer + scaler + step)
when_not_to_use:
  - Fine-tuning an existing pretrained LLM with adapters — use lora-qlora-finetune
  - Training a graph neural network — use build-train-gnn
  - Training sentence/embedding models with contrastive loss — use embedding-model-training
  - Scoring / benchmarking a trained model on a test set — use ml-model-eval
  - You just want a working model fast with no loop control — use HF Trainer or Lightning
keywords: [pytorch, training-loop, backpropagation, amp, mixed-precision, gradscaler, gradient-accumulation, checkpointing, nanogpt, transformer, dataloader, nan-loss, lr-schedule, grad-clipping, autocast]
similar_to: [build-train-gnn, lora-qlora-finetune, embedding-model-training, ml-model-eval]
inputs_needed: PyTorch >= 2.1 installed; a dataset (tensors, or a text file for the GPT recipe); optionally a CUDA/MPS GPU (CPU works for the smoke test)
produces: A runnable training script with AMP, accumulation, LR schedule, grad clip and resumable checkpoints, plus a minimal trainable GPT and a NaN/not-learning/OOM debug checklist
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Neural Net From Scratch (PyTorch training loop)

Own every line of the loop. This skill gives you a correct, resumable PyTorch training
loop with the pieces real training needs — AMP, gradient accumulation, LR warmup+cosine,
grad clipping, checkpointing — plus a minimal GPT you can train on any text file, and a
diagnostic playbook for the three bugs everyone hits.

Model architecture and loop are grounded against **karpathy/nanoGPT** (MIT). This is a
teaching/authoring skill; every snippet below runs on today's PyTorch (>= 2.1), using the
current `torch.amp` API (not the deprecated `torch.cuda.amp.*`).

## When to use

Reach for this when you are writing the loop yourself and need it *correct*: the batching,
the autocast/scaler dance, the accumulation-then-step ordering, and resume. Also when a run
is misbehaving (NaN, flat loss, OOM) and you need a systematic checklist instead of guessing.

If you only want a model trained with minimal code, a `Trainer` is faster — see the
when_not_to_use list. Come here when you need the control or the understanding.

## Prerequisites

- `python3 -c "import torch; print(torch.__version__)"` → 2.1+ (this Mac's python3 is 3.9).
- Device: CUDA gives real AMP speedups (fp16/bf16); Apple MPS works for compute but AMP/GradScaler is a no-op there; CPU is fine for the smoke test.
- No dataset? The GPT recipe trains on a plain `.txt` with a char tokenizer — zero downloads.
- `pip install torch numpy` (CPU wheel is enough to verify correctness).

Key API facts (current, verified):
- Autocast: `torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16)`.
- Scaler: `torch.amp.GradScaler("cuda", enabled=(dtype=="float16"))`. **fp16 needs a scaler; bf16 does not** (its dynamic range doesn't underflow gradients).
- On CPU/MPS wrap the forward in `contextlib.nullcontext()` and disable the scaler.

## Recipe 1 — The canonical training loop (any model/data)

The load-bearing ordering: **scale → backward → (accumulate) → unscale → clip → step →
update → zero**. Get this wrong and you silently train on unclipped or double-counted grads.

```python
import contextlib, math, torch
from torch.utils.data import DataLoader

def make_ctx_and_scaler(device_type, dtype="bfloat16"):
    ptdtype = {"float32": torch.float32, "bfloat16": torch.bfloat16, "float16": torch.float16}[dtype]
    if device_type == "cuda":
        ctx = torch.amp.autocast(device_type="cuda", dtype=ptdtype)
    else:
        ctx = contextlib.nullcontext()          # CPU/MPS: run in fp32
    scaler = torch.amp.GradScaler(device_type, enabled=(dtype == "float16" and device_type == "cuda"))
    return ctx, scaler

def get_lr(step, *, warmup, max_steps, lr, min_lr):
    if step < warmup:                            # linear warmup
        return lr * (step + 1) / (warmup + 1)
    if step >= max_steps:
        return min_lr
    ratio = (step - warmup) / (max_steps - warmup)
    coeff = 0.5 * (1.0 + math.cos(math.pi * ratio))   # cosine decay to min_lr
    return min_lr + coeff * (lr - min_lr)

def train(model, dataset, *, device, steps=2000, batch_size=64, accum=1,
          lr=3e-4, min_lr=3e-5, warmup=100, weight_decay=0.1, grad_clip=1.0,
          dtype="bfloat16", loss_fn=None):
    device_type = "cuda" if "cuda" in str(device) else ("mps" if "mps" in str(device) else "cpu")
    if dtype != "float32" and device_type != "cuda":
        dtype = "float32"                        # AMP only truly helps on CUDA
    ctx, scaler = make_ctx_and_scaler(device_type, dtype)
    model.to(device).train()

    # weight-decay only tensors with dim>=2 (weights), never biases/norms (nanoGPT trick)
    decay = [p for p in model.parameters() if p.dim() >= 2 and p.requires_grad]
    nodecay = [p for p in model.parameters() if p.dim() < 2 and p.requires_grad]
    opt = torch.optim.AdamW(
        [{"params": decay, "weight_decay": weight_decay},
         {"params": nodecay, "weight_decay": 0.0}],
        lr=lr, betas=(0.9, 0.95), eps=1e-8)

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                        drop_last=True, num_workers=2, pin_memory=(device_type == "cuda"))
    it = iter(loader)
    for step in range(steps):
        for g in opt.param_groups:               # apply LR schedule
            g["lr"] = get_lr(step, warmup=warmup, max_steps=steps, lr=lr, min_lr=min_lr)

        opt.zero_grad(set_to_none=True)
        for micro in range(accum):               # gradient accumulation
            try:
                xb, yb = next(it)
            except StopIteration:
                it = iter(loader); xb, yb = next(it)
            xb, yb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True)
            with ctx:
                out = model(xb)
                loss = loss_fn(out, yb) if loss_fn else model.loss(out, yb)
                loss = loss / accum              # normalise so grads == mean over accum
            scaler.scale(loss).backward()        # no-op scaling when scaler disabled

        if grad_clip:
            scaler.unscale_(opt)                 # must unscale BEFORE clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        scaler.step(opt)                         # skips step if grads are inf/nan (fp16)
        scaler.update()

        if step % 100 == 0:
            print(f"step {step:5d} | loss {loss.item()*accum:.4f} | lr {opt.param_groups[0]['lr']:.2e}")
    return model
```

Why each piece exists:
- **`loss / accum`** — accumulating `backward()` *sums* grads; dividing makes the effective batch a true mean, matching a single big batch.
- **`unscale_` before clip** — grads are scaled by the loss scaler; clipping the scaled grads clips the wrong magnitude.
- **`set_to_none=True`** — frees grad tensors (less memory) and avoids stale-grad accumulation bugs.
- **`scaler.step` not `opt.step`** — the scaler inspects for inf/nan (from fp16 overflow) and skips the update, then lowers the scale.

## Recipe 2 — Resumable checkpoints

Save *everything* needed to bit-for-bit continue: model, optimizer, scaler, and the step.
Optimizer momentum and the AMP scale are state — dropping them restarts the dynamics.

```python
def save_ckpt(path, model, opt, scaler, step, best_val, cfg):
    torch.save({"model": model.state_dict(), "opt": opt.state_dict(),
                "scaler": scaler.state_dict(), "step": step,
                "best_val": best_val, "cfg": cfg}, path)

def load_ckpt(path, model, opt=None, scaler=None, map_location="cpu"):
    ck = torch.load(path, map_location=map_location)   # add weights_only=True if untrusted
    model.load_state_dict(ck["model"])
    if opt is not None:    opt.load_state_dict(ck["opt"])
    if scaler is not None: scaler.load_state_dict(ck["scaler"])
    return ck["step"], ck.get("best_val", float("inf")), ck.get("cfg", {})
```

Rules: save on a schedule *and* on best-val (keep both — best for eval, last for resume).
Load model weights before moving optimizer state to device. On resume, re-seed and feed the
saved `step` back into `get_lr` so the schedule continues rather than re-warming up.

## Recipe 3 — A minimal GPT you can actually train

~130 lines, nanoGPT-shaped: pre-LN blocks, causal self-attention via
`F.scaled_dot_product_attention` (uses Flash when available), weight-tied head. Trains on any
`.txt` with a char tokenizer — no downloads. See `scripts/min_gpt.py` for the full, smoke-tested file.

Core pieces (the parts people get wrong):

```python
import torch, torch.nn as nn, torch.nn.functional as F

class Block(nn.Module):
    def __init__(self, d, h, ctx):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.attn = CausalSelfAttention(d, h, ctx)
        self.mlp = nn.Sequential(nn.Linear(d, 4*d), nn.GELU(), nn.Linear(4*d, d))
    def forward(self, x):
        x = x + self.attn(self.ln1(x))           # PRE-LN: norm inside the residual branch
        x = x + self.mlp(self.ln2(x))
        return x

class CausalSelfAttention(nn.Module):
    def __init__(self, d, h, ctx):
        super().__init__(); assert d % h == 0
        self.h, self.d = h, d
        self.qkv = nn.Linear(d, 3*d); self.proj = nn.Linear(d, d)
    def forward(self, x):
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(self.d, dim=2)
        q = q.view(B, T, self.h, C//self.h).transpose(1, 2)   # (B, h, T, hd)
        k = k.view(B, T, self.h, C//self.h).transpose(1, 2)
        v = v.view(B, T, self.h, C//self.h).transpose(1, 2)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)  # causal mask for free
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.proj(y)
```

The `loss` method used by Recipe 1's loop:

```python
def loss(self, logits, targets):
    # logits (B,T,V), targets (B,T); ignore_index=-1 lets you mask padding
    return F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=-1)
```

Weight tying (`self.head.weight = self.tok_emb.weight`) saves params and helps small models.
Init matters: `nn.init.normal_(p, mean=0, std=0.02)`, and scale residual-projection weights
by `1/sqrt(2*n_layers)` — skipping this is a common cause of slow/unstable training.

## Verify

Smoke-test the GPT end-to-end on CPU in ~30s — loss must fall from ~ln(vocab) toward near-zero on a tiny repeated corpus:

```bash
cd /Users/seb.duffy/Documents/GitHub/SEBSKILLS/skills/ml/neural-net-from-scratch
python3 scripts/min_gpt.py --smoke        # trains ~200 steps on synthetic text, asserts loss drops
```

Sanity checks that catch most bugs before a long run:
- **Overfit one batch.** Disable shuffling, feed a single batch for 100 steps — loss must reach ~0. If it can't, the model/label wiring is broken, not the data.
- **Initial loss sanity.** For classification/LM, step-0 loss ≈ `ln(num_classes)` (e.g. ln(65)≈4.17 for a 65-char vocab). Wildly off ⇒ bad init or label offset.
- **Grad norm printed each step** should be finite and neither ~0 (nothing learning) nor exploding.

## Pitfalls

- **fp16 without a GradScaler → instant NaN.** fp16 gradients underflow; the scaler exists to fix exactly this. Prefer **bf16 on Ampere+ (no scaler needed)**; use fp16+scaler only on older GPUs.
- **Clipping scaled gradients.** Always `scaler.unscale_(opt)` before `clip_grad_norm_`, else you clip the wrong magnitude.
- **Forgetting `optimizer.zero_grad()`** (or calling it mid-accumulation) — grads carry over and you train on a stale sum. Zero once *before* the accumulation inner loop.
- **LR too high = NaN; too low = flat loss.** First move when NaN: drop LR 3–10×, add/keep warmup, confirm grad clipping is on. Transformers usually need warmup — no warmup + high LR diverges in the first hundred steps.
- **Loss flat from step 0** — almost always labels: off-by-one targets, wrong `ignore_index`, all-padding batches, or `model.train()` never called (dropout/BN stuck). Overfit-one-batch isolates it.
- **CUDA OOM** — lower `batch_size` and raise `accum` (same effective batch, less memory), enable `torch.utils.checkpoint` (activation checkpointing), use bf16, and `zero_grad(set_to_none=True)`. `nvidia-smi` mid-run to see the real ceiling.
- **`.item()` / `print` every step** forces a GPU→CPU sync and stalls the pipeline — log every N steps.
- **Non-deterministic runs** — seed `torch`, `numpy`, `random`; `num_workers>0` reorders data unless you seed workers. Full determinism also needs `torch.use_deterministic_algorithms(True)` (slower).
- **`torch.load` of untrusted checkpoints** executes pickled code — pass `weights_only=True` for anything you didn't produce.

## Credits

Model shape, param-group weight decay, LR schedule and the accumulate→unscale→clip→step
ordering are adapted from **karpathy/nanoGPT** (MIT License). API modernised to `torch.amp`.
