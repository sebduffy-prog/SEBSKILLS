#!/usr/bin/env python3
"""Dependency-free first-pass provenance scan for a media file.

Detects whether a C2PA / Content Credentials manifest appears to be EMBEDDED
in the file by scanning for the JUMBF box and known C2PA markers, and pulls a
few basic JPEG EXIF fields. It does NOT validate signatures or trust chains --
use `c2patool <file>` for a cryptographically verified report, and the SynthID
Detector portal for watermark detection (SynthID cannot be checked locally).

Usage:  python3 provenance_scan.py <file> [<file> ...]
Exit 0 if a C2PA marker was found in ANY file, else 1.

Stdlib only. Python 3.6+.
"""
import sys
import struct

# Byte markers that indicate an embedded C2PA / Content Credentials manifest.
C2PA_MARKERS = [b"jumb", b"c2pa", b"contentauth", b"urn:uuid:", b"c2pa.assertions"]
SCAN_LIMIT = 8 * 1024 * 1024  # cap scan at 8 MB to stay fast on large media


def scan_c2pa(data):
    """Return the list of C2PA markers found in the byte stream."""
    return [m.decode("ascii", "replace") for m in C2PA_MARKERS if m in data]


def jpeg_exif_fields(data):
    """Best-effort pull of a couple of human-useful JPEG fields (dependency-free).

    We only surface presence of an EXIF/APP1 segment and any embedded XMP, which
    is where 'Software' / edit history and some provenance hints live. Full EXIF
    parsing is out of scope -- point users at exiftool for that.
    """
    hints = {}
    if data[:2] != b"\xff\xd8":  # not a JPEG
        return hints
    hints["has_exif_app1"] = b"Exif\x00\x00" in data[:SCAN_LIMIT]
    hints["has_xmp"] = b"http://ns.adobe.com/xap/1.0/" in data[:SCAN_LIMIT]
    # Common generative-AI software tags leave fingerprints in XMP/EXIF text.
    for tag in (b"Midjourney", b"DALL-E", b"Firefly", b"Stable Diffusion",
                b"Adobe Firefly", b"Google", b"Imagen"):
        if tag in data[:SCAN_LIMIT]:
            hints.setdefault("ai_software_hints", []).append(tag.decode())
    return hints


def scan_file(path):
    try:
        with open(path, "rb") as fh:
            data = fh.read(SCAN_LIMIT)
    except OSError as exc:  # fail loud, never silently swallow
        return {"path": path, "error": str(exc)}
    return {
        "path": path,
        "c2pa_markers": scan_c2pa(data),
        "exif": jpeg_exif_fields(data),
    }


def main(argv):
    if len(argv) < 2:
        print("usage: provenance_scan.py <file> [<file> ...]", file=sys.stderr)
        return 2
    found_any = False
    for path in argv[1:]:
        result = scan_file(path)
        if "error" in result:
            print(f"[ERROR] {path}: {result['error']}", file=sys.stderr)
            continue
        markers = result["c2pa_markers"]
        verdict = "C2PA MARKER PRESENT" if markers else "no C2PA marker found"
        found_any = found_any or bool(markers)
        print(f"== {path} ==")
        print(f"  provenance: {verdict}" + (f" ({', '.join(markers)})" if markers else ""))
        exif = result["exif"]
        if exif:
            if exif.get("has_exif_app1"):
                print("  jpeg: EXIF/APP1 segment present")
            if exif.get("has_xmp"):
                print("  jpeg: XMP metadata present")
            if exif.get("ai_software_hints"):
                print(f"  jpeg: AI-software text hints -> {', '.join(exif['ai_software_hints'])}")
        print("  note: run `c2patool " + path + "` for a signed/validated report;")
        print("        SynthID watermark can only be checked at the SynthID Detector portal.")
    return 0 if found_any else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
