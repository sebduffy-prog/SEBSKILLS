---
name: ai-provenance-deepfake-check
category: verification
description: >-
  Verify whether an image, video, or audio file is AI-generated, edited, or
  authentic by reading C2PA / Content Credentials manifests, checking for
  SynthID watermarks, running lightweight forensic sniffs, and signing your own
  assets with provenance. Trigger when asked "is this real / AI / a deepfake",
  "check the source of this photo", "does this have Content Credentials", "add
  provenance to our creative", or when vetting UGC, influencer, stock, or
  supplied media before it goes into a campaign.
when_to_use:
  - A client, journalist, or teammate asks whether a supplied image/video/audio is AI-generated or manipulated
  - Vetting user-generated, influencer, or stock media before using it in an advertising campaign
  - Reading and validating C2PA / Content Credentials manifests embedded in a file
  - Checking a Google/OpenAI-origin asset for a SynthID watermark
  - Signing your own agency creative with Content Credentials so it carries verifiable provenance
  - Running a fast triage sniff across a batch of files to flag which ones lack any provenance
when_not_to_use:
  - Pure EXIF/metadata read or strip with no authenticity question — use a plain exiftool/`pdf`/`docx` workflow
  - Fact-checking claims or sources in text/documents rather than media authenticity — use deep-research
  - Building the campaign creative itself rather than verifying it — use canvas-design or frontend-design
  - Moderating content for policy/brand-safety at scale — that is a classifier/vendor pipeline, not this skill
keywords:
  - c2pa
  - content credentials
  - provenance
  - synthid
  - deepfake
  - ai-generated
  - watermark
  - authenticity
  - c2patool
  - manifest
  - forensics
  - media-verification
  - cai
  - metadata
  - misinformation
similar_to:
  - deep-research
  - verification-before-completion
inputs_needed: >-
  The media file(s) to check (image/video/audio) locally on disk or a URL to
  download; for signing, a manifest definition JSON and (for production) an
  X.509 signing cert + key. Optional: browser access for the SynthID Detector
  and contentcredentials.org/verify web portals.
produces: >-
  A provenance verdict per file — C2PA manifest present/absent + validation
  status, forensic/metadata hints, and a SynthID check route — plus, when
  requested, a re-signed output file carrying an embedded Content Credentials
  manifest.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# AI Provenance & Deepfake Check

Establish whether a piece of media is authentic, edited, or AI-generated, and attach verifiable provenance to your own assets. Three complementary signals, none of them individually conclusive:

1. **C2PA / Content Credentials** — a cryptographically signed manifest embedded in the file recording who made it, with what tool, and what edits happened. Verifiable and tamper-evident, but only present if a C2PA-enabled tool wrote it (Adobe, Leica, some cameras, OpenAI, Google).
2. **SynthID** — an imperceptible watermark Google DeepMind embeds in AI output from Gemini, Imagen, Lyria, Veo — and, since the OpenAI×DeepMind partnership, ChatGPT/DALL·E/Codex images. Detectable only via Google's SynthID Detector portal (image/audio/video/text); there is no local library for media.
3. **Forensics + metadata** — EXIF/XMP fingerprints, editing-software tags, error-level oddities. Weak, spoofable hints — supporting evidence, never proof.

> Honesty rule: no tool proves a file is "real." Absence of a manifest or watermark is **not** evidence of authenticity — most genuine phone photos carry neither. Report what each signal does and does not tell you.

## When to use

Use when someone hands you media and asks "is this real / AI / a deepfake?", when vetting UGC/influencer/stock before a campaign, or when you need to stamp agency creative with provenance so it survives downstream scrutiny.

## Prerequisites

- **c2patool** — the C2PA reference CLI. No brew on this Mac, so download the binary from the [c2pa-rs releases](https://github.com/contentauth/c2pa-rs/releases?q=c2patool) (`c2patool-vX.Y.Z-universal-apple-darwin.zip`), unzip, and put it on `PATH`. Verify with `c2patool -V`. (On a machine with Homebrew: `brew install c2patool`.)
- **Optional Python API**: `pip3 install c2pa` (package `c2pa`, currently 1.4.x). Needs a recent Python; the system 3.9 here may not have a wheel — prefer the CLI if `pip3 install c2pa` fails.
- **SynthID Detector** — a **web portal** (early-access): <https://deepmind.google/technologies/synthid/synthid-detector/>. No local API for images/audio/video. Only SynthID **text** is open-sourced (Hugging Face Transformers ≥4.46, `SynthIDTextWatermarkingConfig`) — see the text recipe below.
- **Signing certs** — for production Content Credentials you need an X.509 cert + private key. For local testing, c2patool ships test creds so you can sign without your own PKI.
- **scripts/provenance_scan.py** — bundled, stdlib-only, no install. Fast first-pass triage before reaching for c2patool.

## Recipe 1 — Fast triage sniff (no install)

Flag which files even *have* a C2PA marker, plus quick metadata hints, across a batch:

```bash
python3 scripts/provenance_scan.py asset1.jpg asset2.png clip.mp4
```

Prints per file: whether a C2PA/JUMBF marker is embedded, EXIF/XMP presence, any AI-software text fingerprints (Midjourney/Firefly/etc.), and the next step. Exit code 0 if any file had a marker. This does **not** validate signatures — it only tells you what to inspect properly.

## Recipe 2 — Read & validate a C2PA manifest (authoritative)

```bash
# Summary JSON report (signer, claim generator, ingredients, edit actions)
c2patool suspect.jpg

# Full low-level manifest incl. assertions and validation status
c2patool --detailed suspect.jpg
```

Read the report for:
- **`validation_status`** — a valid entry means the signature checks out and the asset is unmodified since signing. Errors here mean the manifest was tampered with or the cert doesn't chain to a trusted root.
- **`claim_generator`** — the software that made/edited it (e.g. `Adobe Firefly`, `Photoshop`, `OpenAI`).
- **`assertions`** → `c2pa.actions` — the edit history (created, colorAdjustments, AI-generated, etc.).
- **`ingredients`** — parent assets that were composited in (chain of provenance).

For a non-CLI, shareable view, upload the file to the official **Verify** tool: <https://contentcredentials.org/verify>.

## Recipe 3 — SynthID watermark check

- **Images / audio / video**: upload the file to the **SynthID Detector** portal. It returns whether a SynthID watermark is present (watermarked / not detected / uncertain), robust to crop, filters, and lossy compression. Use `claude-in-chrome` to drive the portal if you want it automated. There is currently no offline detector for media.
- **Text** (open-source, local): SynthID text watermarking/detection lives in Hugging Face Transformers.

```python
# Text-only, requires: pip install "transformers>=4.46" torch
from transformers import AutoModelForCausalLM, AutoTokenizer, SynthIDTextWatermarkingConfig

wm = SynthIDTextWatermarkingConfig(keys=[654, 400, 836, 123, 340], ngram_len=5)
# pass watermarking_config=wm to model.generate(...); detection uses the
# Bayesian detector shipped in Transformers -> watermarked / not / uncertain.
```

Note: SynthID absence never means "human-made" — most AI tools don't embed it, and the watermark can be stripped by heavy transcoding.

## Recipe 4 — Sign your own asset with Content Credentials

Give agency creative verifiable provenance. Write a manifest definition, then embed it:

```jsonc
// manifest.json
{
  "claim_generator": "VCCP/1.0",
  "assertions": [
    { "label": "c2pa.actions",
      "data": { "actions": [ { "action": "c2pa.created" } ] } },
    { "label": "stds.schema-org.CreativeWork",
      "data": { "@context": "https://schema.org",
                "@type": "CreativeWork",
                "author": [ { "@type": "Organization", "name": "VCCP" } ] } }
  ]
}
```

```bash
# Uses c2patool's built-in test signer (fine for demos/testing)
c2patool --manifest manifest.json --output signed.jpg original.jpg

# Confirm it round-trips
c2patool signed.jpg
```

For production, supply a real X.509 cert + key via the manifest's signing config (see the [c2patool manifest](https://github.com/contentauth/c2pa-rs/blob/main/cli/docs/manifest.md) and [x_509](https://github.com/contentauth/c2pa-rs/blob/main/cli/docs/x_509.md) docs). Never ship the test credentials as real provenance.

## Verify

- `python3 scripts/provenance_scan.py <file>` runs and reports a verdict without errors.
- `c2patool -V` prints a version; `c2patool <signed-file>` shows the manifest you added with a passing validation status.
- Cross-check a known Adobe/Firefly or OpenAI-generated asset: it should show a C2PA manifest (and, for Google/OpenAI images, a SynthID hit in the portal). A raw phone photo should show neither — confirming the tools distinguish signal from absence.

## Pitfalls

- **Absence ≠ authentic.** The single biggest error. No manifest and no watermark is the *normal* state for genuine media. Only positive signals carry weight.
- **Manifests can be stripped.** Screenshotting, re-encoding, or a metadata-scrubbing CDN removes C2PA data. A missing manifest on a re-uploaded file tells you nothing about the original.
- **Validation status matters, not mere presence.** A manifest with `validation_status` errors is worse than none — it may have been tampered. Always read the status, don't just confirm a manifest exists.
- **SynthID is web-only for media + Google/OpenAI-scoped.** It cannot flag Midjourney, Stable Diffusion, or most other generators. Don't present a "no SynthID" result as "not AI."
- **Forensic classifiers are unreliable.** Third-party "deepfake detector" scores (Hive, Sensity, Reality Defender, and countless free sites) have high false-positive/negative rates and are easily gamed. Treat any single score as a weak prior; never state a conclusion from one classifier.
- **Don't fabricate a verdict.** If signals conflict or are absent, say so and recommend human review or the vendor's own provenance — a false "verified authentic" is a reputational risk for the agency and client.
- **Chain of custody.** Verify the file the client actually received/published, not a re-saved copy — each hop can add or lose provenance.
