#!/usr/bin/env python3
"""Run untrusted, LLM-generated Python in an E2B sandbox with hard timeout + guaranteed teardown.

Usage:
    export E2B_API_KEY=e2b_...
    python3 run_in_sandbox.py --file model_output.py --timeout 60
    echo "print(2**10)" | python3 run_in_sandbox.py --timeout 30

Prints JSON to stdout: {"ok", "stdout", "stderr", "error", "results"}.
Never raises the sandboxed code's exception into this process — errors are captured.
Requires: pip install e2b-code-interpreter  (Python 3.9+).
"""
import argparse
import json
import sys

DEFAULT_TIMEOUT_S = 60


def run(code: str, timeout_s: int) -> dict:
    try:
        from e2b_code_interpreter import Sandbox
    except ImportError:
        return {
            "ok": False,
            "error": "e2b-code-interpreter not installed. Run: pip install e2b-code-interpreter",
            "stdout": "", "stderr": "", "results": [],
        }

    sbx = None
    try:
        # timeout = wall-clock lifetime of the whole sandbox VM.
        sbx = Sandbox.create(timeout=timeout_s)
        # request_timeout guards a single execution call from hanging forever.
        execution = sbx.run_code(code, request_timeout=timeout_s)
        err = execution.error
        return {
            "ok": err is None,
            "stdout": "".join(execution.logs.stdout),
            "stderr": "".join(execution.logs.stderr),
            "error": None if err is None else f"{err.name}: {err.value}",
            # Rich results (charts, dataframes, images) surface here as serialisable dicts.
            "results": [str(r.text) for r in execution.results if getattr(r, "text", None)],
        }
    except Exception as exc:  # network / auth / quota — never crash the caller
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "stdout": "", "stderr": "", "results": []}
    finally:
        if sbx is not None:
            try:
                sbx.kill()  # ALWAYS reclaim the VM, even on error
            except Exception:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Run code in an ephemeral E2B sandbox.")
    ap.add_argument("--file", help="Path to a .py file; if omitted, read from stdin.")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                    help=f"Wall-clock seconds before kill (default {DEFAULT_TIMEOUT_S}).")
    args = ap.parse_args()

    code = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    if not code.strip():
        print(json.dumps({"ok": False, "error": "no code supplied"}))
        return 2

    result = run(code, args.timeout)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
