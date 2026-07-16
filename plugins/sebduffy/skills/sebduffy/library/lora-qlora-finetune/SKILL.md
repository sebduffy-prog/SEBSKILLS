---
name: lora-qlora-finetune
category: ml
description: >
  Fine-tune an open LLM cheaply with LoRA/QLoRA. Use to adapt Llama/Qwen/Mistral/Gemma on a
  single consumer GPU via Unsloth or plain PEFT+TRL, pick rank/alpha/target_modules, 4-bit
  QLoRA quantisation, build a chat-template dataset, train with SFTTrainer, then merge to
  16-bit or export GGUF (q4_k_m/q8_0) for Ollama/llama.cpp local inference. Trigger on "fine-tune
  a model", LoRA, QLoRA, PEFT, adapter, Unsloth, GGUF export, or "train on my data".
when_to_use:
  - Adapting an open-weight LLM to a domain/task/style on one 8-24GB GPU without full fine-tuning
  - You have a few hundred to tens of thousands of instruction/chat examples and want cheap SFT
  - You need a merged 16-bit model or a GGUF for Ollama/llama.cpp local inference after training
  - Choosing LoRA hyperparameters (rank, alpha, target_modules, learning rate, dropout)
  - Deciding between QLoRA (4-bit, lowest VRAM) and 16-bit LoRA for a given GPU budget
when_not_to_use:
  - Training embedding/retrieval models — use embedding-model-training
  - Building/training graph neural nets — use build-train-gnn
  - Learning backprop mechanics from primitives — use neural-net-from-scratch
  - Only measuring an existing model's quality — use ml-model-eval
  - Full-parameter pretraining or RLHF/DPO from scratch (this is SFT + LoRA only)
keywords: [lora, qlora, peft, unsloth, trl, sft, finetune, quantization, 4bit, bitsandbytes, gguf, llama, adapter, rank, alpha, ollama]
similar_to: [build-train-gnn, neural-net-from-scratch, embedding-model-training, ml-model-eval]
inputs_needed: A CUDA GPU (>=8GB for 7-8B QLoRA), an instruction/chat dataset (JSONL or HF dataset), a base model id, optionally a HF token for gated models/push.
produces: A trained LoRA adapter (~50-300MB), optionally a merged 16-bit model and a GGUF quant for local inference, plus a runnable training script.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# LoRA / QLoRA Fine-Tuning

Adapt an open LLM to your task by training a tiny low-rank adapter (typically <1% of params)
instead of all weights. QLoRA loads the frozen base in 4-bit so a 7-8B model fits in ~8-12GB.

## When to use

Reach for this when you want a cheap, reproducible SFT run on your own instruction/chat data
and a portable artifact (adapter, merged model, or GGUF). Two backends are covered:
**Unsloth** (fastest, lowest VRAM, easiest GGUF export) and **plain PEFT + TRL** (maximum
control, works anywhere `transformers` runs). Prefer Unsloth unless you need a model it does
not yet patch.

## Prerequisites

- **GPU + CUDA.** LoRA/QLoRA needs an NVIDIA GPU. This does NOT run on Apple Silicon/MPS for
  training (bitsandbytes 4-bit is CUDA-only). Run on Colab, a cloud box, or a Linux workstation.
  Rough VRAM: 7-8B QLoRA ~8-12GB, 13B ~16GB, 70B QLoRA ~40-48GB.
- **Python 3.10-3.12** (not 3.9). Unsloth needs a recent torch.
- Install (pick one backend):
  ```bash
  # Unsloth (recommended) — pulls a matched torch/bitsandbytes/trl/peft stack
  pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
  # or the simple wheel on a fresh CUDA box:
  pip install unsloth

  # Plain PEFT + TRL stack (no Unsloth)
  pip install -U transformers peft trl bitsandbytes accelerate datasets
  ```
- **HF token** only for gated bases (Llama, Gemma): `huggingface-cli login` or `HF_TOKEN=...`.
- A dataset: JSONL with a `messages` list (chat) or `instruction`/`output` fields, or any HF dataset.

## Concepts (get these right or you waste the run)

- **rank `r`** — adapter capacity. Start `r=16`. Small/stylistic task: 8. Hard/knowledge-heavy: 32-64.
- **`lora_alpha`** — scaling. A safe default is `alpha = r` (Unsloth) or `alpha = 2*r`. The effective
  scale is `alpha/r`; changing `r` without `alpha` silently changes the learning signal.
- **`target_modules`** — which projections get adapters. Best results adapt ALL linear layers:
  `["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]`. Attention-only (q/v)
  is cheaper but weaker.
- **`lora_dropout`** — `0` is fastest and fine for most SFT; `0.05-0.1` if overfitting.
- **QLoRA vs 16-bit LoRA** — QLoRA = frozen base in 4-bit (nf4) + LoRA in bf16. Lowest VRAM,
  tiny quality cost. Use 16-bit LoRA only if you have spare VRAM and want the last bit of quality.
- **learning rate** — `2e-4` is the LoRA default (10-50x higher than full fine-tune). Lower to
  `1e-4` for large `r` or instability.
- **epochs** — 1-3. More overfits fast on small sets; watch eval loss, not train loss.

## Recipe A — Unsloth (fast path, recommended)

```python
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset
import torch

MAX_SEQ = 2048
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name   = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",  # pre-quantised, fast download
    max_seq_length = MAX_SEQ,
    load_in_4bit = True,     # QLoRA. Set False for 16-bit LoRA.
    dtype        = None,     # None = auto (bf16 on Ampere+, else fp16)
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj","k_proj","v_proj","o_proj",
                      "gate_proj","up_proj","down_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",  # Unsloth's memory-efficient variant
    random_state = 3407,
)

# --- Dataset: format to the model's chat template ---
tokenizer = get_chat_template(tokenizer, chat_template="llama-3.1")
ds = load_dataset("json", data_files="train.jsonl", split="train")  # each row: {"messages":[...]}

def to_text(batch):
    return {"text": [tokenizer.apply_chat_template(m, tokenize=False,
                     add_generation_prompt=False) for m in batch["messages"]]}
ds = ds.map(to_text, batched=True)

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = ds,
    args = SFTConfig(
        dataset_text_field = "text",
        max_seq_length = MAX_SEQ,
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,   # effective batch = 8
        warmup_steps = 5,
        num_train_epochs = 1,              # or max_steps = 60 for a smoke test
        learning_rate = 2e-4,
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
        report_to = "none",                # set "wandb" to track
    ),
)
trainer.train()

# --- Save ---
model.save_pretrained("lora_adapter"); tokenizer.save_pretrained("lora_adapter")  # adapter only
model.save_pretrained_merged("merged_16bit", tokenizer, save_method="merged_16bit")
model.save_pretrained_gguf("gguf", tokenizer, quantization_method="q4_k_m")        # Ollama/llama.cpp
```

Only train on completions (mask the prompt) to boost quality — wrap with Unsloth's
`train_on_responses_only(trainer, instruction_part=..., response_part=...)` using the template's
turn markers (e.g. Llama-3's `<|start_header_id|>user` / `assistant`).

## Recipe B — Plain PEFT + TRL (portable, full control)

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset

base = "Qwen/Qwen2.5-7B-Instruct"
bnb = BitsAndBytesConfig(
    load_in_4bit = True,
    bnb_4bit_quant_type = "nf4",
    bnb_4bit_compute_dtype = torch.bfloat16,
    bnb_4bit_use_double_quant = True,
)
tok = AutoTokenizer.from_pretrained(base)
model = AutoModelForCausalLM.from_pretrained(base, quantization_config=bnb, device_map="auto")
model = prepare_model_for_kbit_training(model)   # enables grad ckpt + casts norms

peft_cfg = LoraConfig(
    r = 16, lora_alpha = 32, lora_dropout = 0.05, bias = "none",
    task_type = "CAUSAL_LM",
    target_modules = ["q_proj","k_proj","v_proj","o_proj",
                      "gate_proj","up_proj","down_proj"],
)
model = get_peft_model(model, peft_cfg)
model.print_trainable_parameters()               # expect <1% trainable

ds = load_dataset("json", data_files="train.jsonl", split="train")
ds = ds.map(lambda r: {"text": tok.apply_chat_template(r["messages"], tokenize=False)})

trainer = SFTTrainer(
    model=model, tokenizer=tok, train_dataset=ds,
    args=SFTConfig(dataset_text_field="text", max_seq_length=2048,
        per_device_train_batch_size=2, gradient_accumulation_steps=4,
        num_train_epochs=1, learning_rate=2e-4, warmup_ratio=0.03,
        optim="paged_adamw_8bit", lr_scheduler_type="cosine",
        logging_steps=10, bf16=True, output_dir="outputs", report_to="none"),
)
trainer.train()
model.save_pretrained("lora_adapter")            # adapter only
```

Merge later for deployment: `PeftModel.from_pretrained(base, "lora_adapter").merge_and_unload()`
then `.save_pretrained(...)`. For GGUF from this path, use llama.cpp's `convert_hf_to_gguf.py`
on the merged model (Unsloth's `save_pretrained_gguf` is the shortcut).

## Verify

1. **It trains, loss falls.** With `logging_steps=1`, train loss should drop steadily (not to 0
   in 5 steps — that means overfit/leak). Run a 60-step smoke test (`max_steps=60`) first.
2. **Adapter loads + generates.** After save, reload and inference one prompt:
   ```python
   FastLanguageModel.for_inference(model)  # Unsloth 2x faster inference
   ids = tokenizer.apply_chat_template([{"role":"user","content":"..."}],
             add_generation_prompt=True, return_tensors="pt").to("cuda")
   print(tokenizer.decode(model.generate(ids, max_new_tokens=128)[0]))
   ```
3. **Held-out eval.** Pass `eval_dataset` + `eval_strategy="steps"`; eval loss should track train
   loss, not diverge. For task quality, score with **ml-model-eval**, not vibes.
4. **GGUF runs locally.** `ollama create mymodel -f Modelfile` (Modelfile `FROM ./gguf/*.gguf`),
   then `ollama run mymodel`. Or `llama-cli -m gguf/model.q4_k_m.gguf -p "..."`.

## Pitfalls

- **Wrong chat template = garbage.** You MUST format data with the base model's exact template
  (`apply_chat_template` / Unsloth `get_chat_template`). A raw `instruction\noutput` string on an
  Instruct model degrades it. Match template to model family (llama-3.1, qwen-2.5, chatml, gemma).
- **No CUDA GPU.** bitsandbytes 4-bit is CUDA-only — training will not work on Mac/MPS or CPU.
  Use the eval/inference-only paths there, or rent a GPU.
- **`alpha` and `r` desync.** If you bump `r`, keep the `alpha/r` ratio intended, or your effective
  LR shifts. Default to `alpha == r` (Unsloth) or `2*r`.
- **OOM.** Lower `per_device_train_batch_size` (raise `gradient_accumulation_steps` to keep effective
  batch), shrink `max_seq_length`, ensure gradient checkpointing is on, use `optim="paged_adamw_8bit"`.
- **Overfitting on small data.** <1k examples: 1 epoch, `r<=16`, add `lora_dropout=0.05`, hold out
  an eval set. Falling train loss with rising eval loss = stop.
- **Loss on the prompt.** Training on the full text (prompt+answer) is fine but weaker; masking the
  prompt (`train_on_responses_only` / completion-only collator) usually improves instruction following.
- **Merging a 4-bit base loses precision.** For a clean merged model, `save_pretrained_merged`
  (Unsloth) dequantises to 16-bit first. Do not naively `merge_and_unload` a 4-bit model in PEFT —
  reload the base in 16-bit before merging the adapter.
- **Version skew.** unsloth/trl/peft/transformers move fast and break each other. Let Unsloth pin
  the stack, or pin your own versions and don't mix a fresh `trl` with an old `transformers`.
- **GGUF export needs llama.cpp.** Unsloth builds it on first `save_pretrained_gguf`; on an offline
  box pre-clone/build llama.cpp or the export step fails.
