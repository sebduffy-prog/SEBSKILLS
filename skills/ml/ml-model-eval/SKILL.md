---
name: ml-model-eval
category: ml
description: >
  Evaluate a trained model like an adult instead of quoting a single accuracy number.
  Pick metrics that match the objective and class balance, plot calibration + confusion
  + ROC/PR curves with torchmetrics, slice errors by subgroup to find where the model
  actually fails, and run standardized LLM benchmarks (MMLU, GSM8K, HellaSwag) with
  EleutherAI lm-evaluation-harness. Use whenever someone says "how good is this model",
  reports only accuracy, is comparing checkpoints/models, or needs a defensible eval report.
when_to_use:
  - You have a trained classifier/regressor/LLM and need a rigorous, honest evaluation
  - Someone reported only accuracy and you suspect class imbalance or miscalibration
  - You are comparing two checkpoints or models and need apples-to-apples metrics
  - You need calibration curves (ECE), confusion matrices, or ROC/PR curves
  - You want to slice errors by subgroup to find where the model fails
  - You need standardized LLM benchmark numbers (MMLU/GSM8K/HellaSwag/ARC) that others trust
when_not_to_use:
  - You are still training the model and want live metrics — use the training-loop logging in build-train-gnn or lora-qlora-finetune instead
  - You need to design an offline experiment / A-B test with significance — that is an experiment-design task, not model eval
  - You only want a leaderboard number for a hosted API model with no local weights — call the provider eval or lm-eval `--model openai-completions`, not the local hf path
  - The task is embedding retrieval quality (recall@k, MRR) — use embedding-model-training's eval section
keywords: [model-evaluation, metrics, calibration, ece, confusion-matrix, roc-auc, pr-curve, torchmetrics, lm-eval-harness, mmlu, gsm8k, error-analysis, slicing, f1, benchmarking]
similar_to: [build-train-gnn, neural-net-from-scratch, lora-qlora-finetune, embedding-model-training]
inputs_needed: Model predictions (probabilities/logits) + ground-truth labels for classical eval; OR a HuggingFace model id / local weights path for LLM benchmarking.
produces: A metrics table, calibration/confusion/ROC-PR plots, a per-slice error breakdown, and (for LLMs) a reproducible lm-eval results.json with task scores + stderr.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# ML Model Evaluation

Rigorous evaluation is choosing the *right* metric, knowing your confidence in it, and
finding *where* the model breaks — not printing one number. This skill covers classical
supervised eval (torchmetrics) and standardized LLM benchmarking (lm-evaluation-harness).

## When to use

Use it the moment "how good is the model?" comes up, especially when the only number on
offer is accuracy. Accuracy lies under class imbalance, hides calibration, and averages
away the subgroups that matter. Follow the three passes below: **metrics → curves → slices**.

## Prerequisites

- Python 3.9+. Classical eval: `pip install torchmetrics torch scikit-learn pandas matplotlib`.
- LLM benchmarking: `pip install "lm_eval[hf]"` (add `vllm` / `api` extras as needed). First run
  downloads model weights + datasets from HuggingFace — needs disk, network, and a GPU for
  anything non-trivial (CPU works for `--limit`-capped smoke tests only).
- Inputs for classical eval: predicted **probabilities** (not just argmax labels — you need
  them for calibration and ROC) as a tensor `preds [N, C]` and integer `target [N]`.
- macOS note: torchmetrics runs on `mps` or `cpu`; lm-eval on Apple silicon is smoke-test only.

## Recipe 1 — Pick the right metric (don't default to accuracy)

| Situation | Report this, not accuracy |
|---|---|
| Imbalanced classes | Macro-F1, balanced accuracy, PR-AUC (not ROC-AUC) |
| Ranking / threshold-free | ROC-AUC (balanced), Average Precision (imbalanced) |
| Cost-sensitive errors | Precision/recall at the operating threshold you'll actually ship |
| Probabilities matter | ECE (calibration) + Brier score alongside a discrimination metric |
| Multiclass | Always inspect the confusion matrix, not just the scalar |

```python
import torch
from torchmetrics.classification import (
    MulticlassF1Score, MulticlassAccuracy, MulticlassCalibrationError,
    MulticlassConfusionMatrix, MulticlassAUROC, MulticlassAveragePrecision,
)

NUM_CLASSES = 4
preds  = torch.softmax(torch.randn(500, NUM_CLASSES), dim=1)  # [N, C] probabilities
target = torch.randint(0, NUM_CLASSES, (500,))               # [N] int labels

metrics = {
    "macro_f1":  MulticlassF1Score(NUM_CLASSES, average="macro"),
    "bal_acc":   MulticlassAccuracy(NUM_CLASSES, average="macro"),
    "auroc":     MulticlassAUROC(NUM_CLASSES, average="macro"),
    "avg_prec":  MulticlassAveragePrecision(NUM_CLASSES, average="macro"),
    # norm='l1' -> Expected Calibration Error; 'max' -> Maximum Calibration Error
    "ece":       MulticlassCalibrationError(NUM_CLASSES, n_bins=15, norm="l1"),
}
for name, m in metrics.items():
    print(f"{name:10s} {m(preds, target).item():.4f}")

print(MulticlassConfusionMatrix(NUM_CLASSES)(preds, target))
```

For binary swap in `BinaryF1Score`, `BinaryAUROC`, `BinaryCalibrationError(...)`, etc.
The functional forms live in `torchmetrics.functional.classification` if you prefer
one-shot calls over stateful objects.

## Recipe 2 — Calibration + reliability diagram

A model can be accurate and badly calibrated (overconfident). ECE quantifies the gap;
the reliability diagram shows *where*. Plot predicted-confidence vs empirical-accuracy per bin.

```python
import numpy as np, matplotlib.pyplot as plt

def reliability(preds, target, n_bins=15):
    conf, pred_cls = preds.max(dim=1)
    correct = (pred_cls == target).float()
    edges = torch.linspace(0, 1, n_bins + 1)
    xs, ys = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            xs.append(conf[m].mean().item())
            ys.append(correct[m].mean().item())
    return xs, ys

xs, ys = reliability(preds, target)
plt.plot([0, 1], [0, 1], "--", color="gray", label="perfect")
plt.plot(xs, ys, "o-", label="model")
plt.xlabel("confidence"); plt.ylabel("accuracy"); plt.legend()
plt.title("Reliability diagram"); plt.savefig("reliability.png", dpi=120)
```

If badly miscalibrated, fit **temperature scaling** on a held-out split (a single scalar
`T` dividing logits before softmax, tuned to minimise NLL) — cheap and usually enough.

## Recipe 3 — Error slicing (find where it fails)

The average metric is a lie of composition. Break performance down by any feature you
have — subgroup, input length, source, difficulty band. A model at 92% overall can be
at 61% on the slice you care about.

```python
import pandas as pd

df = pd.DataFrame({
    "target":  target.numpy(),
    "pred":    preds.argmax(1).numpy(),
    "conf":    preds.max(1).values.numpy(),
    "group":   np.random.choice(["A", "B", "C"], size=len(target)),  # your slice column
})
df["correct"] = df.target == df.pred

slice_report = (df.groupby("group")
                  .agg(n=("correct", "size"),
                       acc=("correct", "mean"),
                       mean_conf=("conf", "mean"))
                  .sort_values("acc"))
print(slice_report)   # worst slice at the top — investigate it, don't ship the average
```

Rules: report the **n** per slice (a 55% slice on n=9 is noise), sort worst-first, and
flag any slice where `mean_conf >> acc` (confidently wrong — the dangerous kind).

## Recipe 4 — Standardized LLM benchmarking (lm-evaluation-harness)

The trusted, reproducible way to get MMLU/GSM8K/HellaSwag/ARC numbers. Never hand-roll
these — subtle prompt/normalisation choices make hand-rolled scores incomparable.

```bash
# Smoke test on CPU/mps first (10 examples) to confirm the pipeline works
lm_eval --model hf \
  --model_args pretrained=EleutherAI/pythia-160m \
  --tasks hellaswag,arc_easy \
  --limit 10 --batch_size 8 \
  --output_path results/ --log_samples

# Real run: 5-shot MMLU + GSM8K on GPU, chat template for instruct models
lm_eval --model hf \
  --model_args pretrained=meta-llama/Llama-3.1-8B-Instruct,dtype=bfloat16 \
  --tasks mmlu,gsm8k \
  --num_fewshot 5 --batch_size auto \
  --device cuda:0 --apply_chat_template \
  --output_path results/ --log_samples
```

- `--tasks` names come from `lm_eval --tasks list` (thousands available; group names like
  `mmlu` expand to all subtasks).
- `--batch_size auto` lets it find the largest fitting batch. `--limit N` caps examples.
- `--log_samples` writes every prompt+response to `results/` — essential for debugging a
  suspicious score. `--use_cache DIR` avoids re-running identical requests.
- Instruct models: pass `--apply_chat_template` (and `--fewshot_as_multiturn`) or scores
  will be wrong. Base models: omit it.

Python API (no `output_path` param — capture the returned dict yourself):

```python
from lm_eval import simple_evaluate
res = simple_evaluate(
    model="hf",
    model_args="pretrained=EleutherAI/pythia-160m",
    tasks=["hellaswag"], num_fewshot=0, limit=10, batch_size=8,
)
for task, scores in res["results"].items():
    print(task, scores)   # e.g. {'acc,none': 0.30, 'acc_stderr,none': 0.14, ...}
```

## Verify

- Metrics sanity: a random-guess baseline should score ~1/C accuracy, ~0.5 AUROC. If your
  "great" model matches that, your labels/preds are misaligned.
- Calibration: ECE near 0 means calibrated; check the reliability plot actually hugs the
  diagonal, don't trust the scalar alone.
- lm-eval: every score comes with `_stderr`. If two models' intervals (`score ± 2·stderr`)
  overlap, the difference is **not** significant — say so. Re-open `results/` samples to
  confirm the model was prompted the way you intended.
- Reproducibility: lm-eval pins a `git_hash` and config in the results JSON — keep it.

## Pitfalls

- **Reporting accuracy on imbalanced data.** A 95%-negative dataset gives 95% accuracy for
  a model that always says "negative". Use macro-F1 / balanced accuracy / PR-AUC.
- **ROC-AUC on heavy imbalance.** ROC-AUC looks flattering; Average Precision (PR-AUC) is
  the honest choice when positives are rare.
- **Feeding argmax labels where probabilities are needed.** Calibration, AUROC, and AP all
  need the probability/logit tensor, not the predicted class.
- **Tuning the threshold on the test set.** Pick your operating threshold on validation,
  then report test metrics at that fixed threshold. Otherwise you're leaking.
- **Trusting a single lm-eval number.** Always report the stderr and the exact task +
  `num_fewshot` + chat-template setting; those choices move scores by several points.
- **Forgetting `--apply_chat_template` for instruct models** (or adding it for base models)
  — the single most common cause of "why is my Llama score garbage".
- **Slices with tiny n.** A worst-slice accuracy on 8 samples is noise; always print n.
