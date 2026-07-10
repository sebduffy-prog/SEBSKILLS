#!/usr/bin/env python3
"""Static consent/tag audit for a saved HTML page or a GTM container export.

Flags the two failures that break advertising compliance:
  1. A Google/analytics/ad tag that loads BEFORE the Consent Mode default block.
  2. A Consent Mode v2 default that is missing or omits a required signal.

Also lists known tracker hostnames found so they can be mapped to a ROPA.
No third-party deps; runs on macOS system python3 (3.9).
"""
import json
import re
import sys

V2_SIGNALS = ("ad_storage", "ad_user_data", "ad_personalization", "analytics_storage")

# Substrings that identify a tag which must not fire before consent.
TRACKERS = (
    "googletagmanager.com/gtm.js", "gtag/js", "google-analytics.com",
    "googleadservices", "googlesyndication", "doubleclick", "googleads",
    "facebook.com/tr", "connect.facebook.net", "snap.licdn.com",
    "analytics.tiktok.com", "sc-static.net", "px.ads", "bat.bing.com",
)

CONSENT_DEFAULT_RE = re.compile(r"""consent['"]?\s*,\s*['"]default['"]""", re.I)


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def audit_html(text):
    findings = []
    m = CONSENT_DEFAULT_RE.search(text)
    if not m:
        findings.append(("ERROR", "No gtag('consent','default',...) block found."))
        default_pos = None
    else:
        default_pos = m.start()
        # Inspect the signals inside a ~600-char window after the default call.
        window = text[m.start(): m.start() + 600]
        missing = [s for s in V2_SIGNALS if s not in window]
        if missing:
            findings.append(("ERROR",
                             "Consent default is missing v2 signal(s): "
                             + ", ".join(missing)))
        else:
            findings.append(("OK", "All four Consent Mode v2 signals present in default."))

    # Order check: is any tracker referenced before the default block?
    for t in TRACKERS:
        idx = text.find(t)
        if idx == -1:
            continue
        if default_pos is None or idx < default_pos:
            findings.append(("ERROR",
                             f"Tracker '{t}' appears before the consent default "
                             f"(pos {idx})."))
    return findings, found_trackers(text)


def audit_gtm(text):
    """Best-effort scan of a GTM workspace JSON export."""
    findings = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [("ERROR", f"Not valid JSON: {exc}")], set()
    blob = json.dumps(data).lower()
    has_consent_init = "consent" in blob and (
        "consent initialization" in blob or "gcs" in blob or "default" in blob)
    if has_consent_init:
        findings.append(("OK", "Container references consent configuration."))
    else:
        findings.append(("ERROR", "No consent-mode configuration found in container."))
    missing = [s for s in V2_SIGNALS if s not in blob]
    if missing:
        findings.append(("WARN", "v2 signal(s) not seen in container JSON: "
                         + ", ".join(missing)))
    return findings, found_trackers(blob)


def found_trackers(text):
    low = text.lower()
    return {t for t in TRACKERS if t in low}


def main(argv):
    if len(argv) != 2:
        print("usage: python3 tag_audit.py <page.html | GTM_export.json>")
        return 2
    path = argv[1]
    text = read(path)
    if path.lower().endswith(".json"):
        findings, trackers = audit_gtm(text)
    else:
        findings, trackers = audit_html(text)

    errors = 0
    for level, msg in findings:
        print(f"[{level}] {msg}")
        if level == "ERROR":
            errors += 1
    if trackers:
        print("\nTracker hostnames found (map each to your ROPA/vendor list):")
        for t in sorted(trackers):
            print(f"  - {t}")
    print(f"\n{errors} error(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
