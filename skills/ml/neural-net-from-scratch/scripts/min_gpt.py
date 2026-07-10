#!/usr/bin/env python3
"""Minimal trainable GPT (nanoGPT-shaped, MIT-adapted) + char tokenizer + training loop.

Runs on CPU/CUDA/MPS. Zero downloads: trains on a .txt file, or synthetic text in --smoke.

Examples:
    python3 min_gpt.py --smoke                       # ~200 steps, asserts loss drops (CI/verify)
    python3 min_gpt.py --data mytext.txt --steps 3000
    python3 min_gpt.py --data mytext.txt --resume ckpt.pt   # continues from checkpoint

Uses the current torch.amp API. bf16 needs no GradScaler; fp16 does (see make_ctx_and_scaler).
"""
import argparse, contextlib, math, os, sys
import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------- model ----------------------------
class CausalSelfAttention(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        assert d % h == 0
        self.h, self.d = h, d
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)

    def forward(self, x):
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(self.d, dim=2)
        q = q.view(B, T, self.h, C // self.h).transpose(1, 2)
        k = k.view(B, T, self.h, C // self.h).transpose(1, 2)
        v = v.view(B, T, self.h, C // self.h).transpose(1, 2)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)  # Flash when available
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.proj(y)


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.attn = CausalSelfAttention(d, h)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))

    def forward(self, x):
        x = x + self.attn(self.ln1(x))   # pre-LN
        x = x + self.mlp(self.ln2(x))
        return x


class MinGPT(nn.Module):
    def __init__(self, vocab, ctx, d=128, h=4, layers=4):
        super().__init__()
        self.ctx = ctx
        self.tok_emb = nn.Embedding(vocab, d)
        self.pos_emb = nn.Embedding(ctx, d)
        self.blocks = nn.ModuleList([Block(d, h) for _ in range(layers)])
        self.ln_f = nn.LayerNorm(d)
        self.head = nn.Linear(d, vocab, bias=False)
        self.head.weight = self.tok_emb.weight     # weight tying
        self.apply(self._init)
        # scale residual-projection weights (nanoGPT / GPT-2 init)
        for name, p in self.named_parameters():
            if name.endswith("proj.weight") or name.endswith("mlp.2.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * layers))

    def _init(self, m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)

    def forward(self, idx):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)[None, :, :]
        for blk in self.blocks:
            x = blk(x)
        return self.head(self.ln_f(x))

    def loss(self, logits, targets):
        return F.cross_entropy(logits.view(-1, logits.size(-1)),
                               targets.view(-1), ignore_index=-1)


# ---------------------------- data ----------------------------
def load_text(path, smoke):
    if smoke or path is None:
        # small structured corpus so a tiny model can learn it fast
        return ("the quick brown fox jumps over the lazy dog. " * 200)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def make_batch(data_ids, ctx, batch_size, device):
    ix = torch.randint(len(data_ids) - ctx - 1, (batch_size,))
    x = torch.stack([data_ids[i:i + ctx] for i in ix])
    y = torch.stack([data_ids[i + 1:i + 1 + ctx] for i in ix])
    return x.to(device), y.to(device)


# ---------------------------- amp helpers ----------------------------
def make_ctx_and_scaler(device_type, dtype):
    ptdtype = {"float32": torch.float32, "bfloat16": torch.bfloat16,
               "float16": torch.float16}[dtype]
    if device_type == "cuda":
        ctx = torch.amp.autocast(device_type="cuda", dtype=ptdtype)
    else:
        ctx = contextlib.nullcontext()
    scaler = torch.amp.GradScaler(device_type,
                                  enabled=(dtype == "float16" and device_type == "cuda"))
    return ctx, scaler


def get_lr(step, warmup, max_steps, lr, min_lr):
    if step < warmup:
        return lr * (step + 1) / (warmup + 1)
    if step >= max_steps:
        return min_lr
    ratio = (step - warmup) / max(1, (max_steps - warmup))
    coeff = 0.5 * (1.0 + math.cos(math.pi * ratio))
    return min_lr + coeff * (lr - min_lr)


# ---------------------------- train ----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--ctx", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--resume", default=None)
    ap.add_argument("--save", default=None)
    args = ap.parse_args()

    if torch.cuda.is_available():
        device = "cuda"
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    device_type = "cuda" if device == "cuda" else ("mps" if device == "mps" else "cpu")
    dtype = args.dtype if device_type == "cuda" else "float32"  # AMP truly helps only on CUDA
    steps = args.steps if args.steps is not None else (200 if args.smoke else 2000)

    torch.manual_seed(0)
    text = load_text(args.data, args.smoke)
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    data_ids = torch.tensor([stoi[c] for c in text], dtype=torch.long)
    vocab = len(chars)
    ctx_len = min(args.ctx, len(data_ids) - 2)

    ctx, scaler = make_ctx_and_scaler(device_type, dtype)
    model = MinGPT(vocab, ctx_len).to(device)
    decay = [p for p in model.parameters() if p.dim() >= 2]
    nodecay = [p for p in model.parameters() if p.dim() < 2]
    opt = torch.optim.AdamW(
        [{"params": decay, "weight_decay": 0.1}, {"params": nodecay, "weight_decay": 0.0}],
        lr=args.lr, betas=(0.9, 0.95))

    start = 0
    if args.resume and os.path.exists(args.resume):
        ck = torch.load(args.resume, map_location=device)
        model.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"])
        scaler.load_state_dict(ck["scaler"]); start = ck["step"]
        print(f"resumed from step {start}")

    warmup = max(1, steps // 20)
    first_loss = last_loss = None
    model.train()
    for step in range(start, steps):
        for g in opt.param_groups:
            g["lr"] = get_lr(step, warmup, steps, args.lr, args.lr / 10)
        xb, yb = make_batch(data_ids, ctx_len, args.batch_size, device)
        opt.zero_grad(set_to_none=True)
        with ctx:
            logits = model(xb)
            loss = model.loss(logits, yb)
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(opt); scaler.update()
        last_loss = loss.item()
        if first_loss is None:
            first_loss = last_loss
            print(f"step 0 loss {first_loss:.4f} (ln(vocab)={math.log(vocab):.4f})")
        if step % 50 == 0:
            print(f"step {step:5d} | loss {last_loss:.4f} | lr {opt.param_groups[0]['lr']:.2e}")

    if args.save:
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(),
                    "scaler": scaler.state_dict(), "step": steps}, args.save)
        print(f"saved {args.save}")

    if args.smoke:
        assert last_loss < first_loss * 0.5, \
            f"smoke FAILED: loss did not halve ({first_loss:.3f} -> {last_loss:.3f})"
        print(f"smoke OK: loss {first_loss:.3f} -> {last_loss:.3f} on {device}")


if __name__ == "__main__":
    sys.exit(main())
