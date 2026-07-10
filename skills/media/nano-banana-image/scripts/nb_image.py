#!/usr/bin/env python3
"""Nano Banana (Gemini Flash Image) generate / edit / fuse — writes a PNG.

Usage:
  export GEMINI_API_KEY=...
  nb_image.py --prompt "..." [--image ref.png ...] --out out.png [--aspect 3:4] [--model gemini-2.5-flash-image]

- No --image  -> text-to-image.
- One --image -> prompt-edit that image (keep subject with "keep identical" phrasing in the prompt).
- Many --image-> multi-image fusion (person + product + background, up to ~14).

Aspect is a hint appended to the prompt on the classic generateContent path (which has no aspect param).
"""
import argparse
import sys

try:
    from google import genai
    from PIL import Image
except ImportError:
    sys.exit("Install deps first:  python3 -m pip install --user google-genai pillow")


def main() -> int:
    p = argparse.ArgumentParser(description="Nano Banana image generate/edit/fuse")
    p.add_argument("--prompt", required=True, help="Instruction. For consistency say 'keep identical'.")
    p.add_argument("--image", action="append", default=[], metavar="PATH",
                   help="Reference image; repeat for multi-image fusion.")
    p.add_argument("--out", required=True, help="Output PNG path.")
    p.add_argument("--aspect", default=None, help="Framing hint, e.g. 3:4, 16:9, 1:1.")
    p.add_argument("--model", default="gemini-2.5-flash-image", help="Gemini image model id.")
    args = p.parse_args()

    # SDK auto-reads GEMINI_API_KEY from the environment; fail fast if it's absent.
    client = genai.Client()

    prompt = args.prompt
    if args.aspect:
        prompt = f"{prompt}\n\nCompose as a {args.aspect} framed image."

    # contents = prompt text followed by any reference images (PIL objects are handled by the SDK).
    contents = [prompt]
    for path in args.image:
        try:
            contents.append(Image.open(path))
        except Exception as exc:  # noqa: BLE001 - surface a clear boundary error
            return _die(f"Could not open reference image '{path}': {exc}")

    try:
        resp = client.models.generate_content(model=args.model, contents=contents)
    except Exception as exc:  # noqa: BLE001 - network/auth/quota all land here
        return _die(f"Gemini request failed: {exc}")

    return _save_first_image(resp, args.out)


def _save_first_image(resp, out_path: str) -> int:
    """Walk response parts, write the first inline image, or surface any text the model returned."""
    text_bits = []
    candidates = getattr(resp, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        for part in (getattr(content, "parts", None) or []):
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                with open(out_path, "wb") as f:
                    f.write(inline.data)  # SDK returns decoded bytes, not base64
                print(f"Wrote {out_path}")
                return 0
            if getattr(part, "text", None):
                text_bits.append(part.text)

    msg = " ".join(text_bits).strip() or "no image and no text returned"
    return _die(f"Model returned NO image. Response text: {msg}")


def _die(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
