#!/usr/bin/env python3
"""feed_tool.py - build, validate and diagnose product feeds for Google
Merchant Center and Meta (Facebook/Instagram) commerce catalogs.

Stdlib only (Python 3.9+). No external deps, no network calls.

Canonical input schema (CSV header row OR a JSON list of objects). One row =
one sellable variant. Recognised keys (superset of both platforms):

    id, title, description, link, image_link, additional_image_link,
    availability, availability_date, price, sale_price, currency,
    brand, gtin, mpn, condition, google_product_category, product_type,
    item_group_id, color, size, gender, age_group, quantity, mobile_link

`price`/`sale_price` may be bare numbers (combined with `currency`, default
GBP) or already "12.99 GBP".

Subcommands:
    validate  --platform google|meta [--json]        exit 1 if any ERROR
    build     --platform google|meta --format xml|tsv|csv  -o OUT
    diagnose  [--json]                               map issues -> likely
                                                     disapproval reasons

Usage:
    feed_tool.py validate products.csv --platform google
    feed_tool.py build products.csv --platform google --format xml -o feed.xml
    feed_tool.py build products.csv --platform meta --format csv -o meta.csv
    feed_tool.py diagnose products.csv
"""
import argparse
import csv
import html
import io
import json
import sys
from datetime import datetime

# --- limits / enums grounded in the official specs -------------------------
TITLE_MAX = 150
DESC_MAX = 5000
ID_MAX = 50
BRAND_MAX = 70
PRODUCT_TYPE_MAX = 750
GTIN_MAX = 50

# Google Merchant Center uses underscores; Meta canonical uses spaces but also
# accepts underscores. We normalise per-platform on output.
GOOGLE_AVAIL = {"in_stock", "out_of_stock", "preorder", "backorder"}
META_AVAIL = {"in stock", "out of stock", "preorder", "available for order",
              "discontinued"}
CONDITION = {"new", "refurbished", "used"}
AGE_GROUP = {"newborn", "infant", "toddler", "kids", "adult"}
GENDER = {"male", "female", "unisex"}

REQUIRED = {
    # link/image_link/price/availability/id/title/description shared;
    # brand strongly required on both. gtin OR mpn identifier.
    "google": ["id", "title", "description", "link", "image_link",
               "availability", "price"],
    "meta": ["id", "title", "description", "link", "image_link",
             "availability", "price", "condition"],
}

SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


# --- helpers ---------------------------------------------------------------
def load_products(path):
    """Read CSV or JSON into a list of dict rows. Fails fast on bad input."""
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError as exc:
        sys.exit(f"cannot read {path}: {exc}")
    stripped = text.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("products", [])
    else:
        rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        sys.exit(f"no products found in {path}")
    return [{k: ("" if v is None else str(v).strip()) for k, v in r.items()}
            for r in rows]


def gtin_valid(gtin):
    """GS1 mod-10 check-digit validation for 8/12/13/14-digit GTINs."""
    g = gtin.strip()
    if not g.isdigit() or len(g) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in g]
    check = digits[-1]
    body = digits[:-1][::-1]  # rightmost body digit gets weight 3
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(body))
    return (10 - total % 10) % 10 == check


def split_price(row, key):
    """Return (amount:str, currency:str) from a price-ish field, or (None,None)."""
    raw = row.get(key, "")
    if not raw:
        return None, None
    parts = raw.split()
    if len(parts) == 2:
        return parts[0], parts[1].upper()
    return parts[0], (row.get("currency") or "GBP").upper()


def price_ok(amount):
    try:
        return float(amount) >= 0
    except (TypeError, ValueError):
        return False


# --- validation ------------------------------------------------------------
def validate_row(row, platform):
    """Yield (severity, field, message) tuples for one product."""
    rid = row.get("id", "?")
    avail_set = GOOGLE_AVAIL if platform == "google" else META_AVAIL

    for field in REQUIRED[platform]:
        if not row.get(field):
            yield ("ERROR", field, f"[{rid}] missing required '{field}'")

    if len(row.get("id", "")) > ID_MAX:
        yield ("ERROR", "id", f"[{rid}] id > {ID_MAX} chars")

    title = row.get("title", "")
    if len(title) > TITLE_MAX:
        yield ("ERROR", "title", f"[{rid}] title {len(title)} > {TITLE_MAX}")
    elif title and len(title) < 20:
        yield ("WARN", "title",
               f"[{rid}] title short ({len(title)}c) - front-load brand+key attrs")
    if title != title.strip() or "  " in title:
        yield ("WARN", "title", f"[{rid}] title has stray/double whitespace")
    if title.isupper() and len(title) > 5:
        yield ("WARN", "title", f"[{rid}] ALL-CAPS title risks disapproval")

    if len(row.get("description", "")) > DESC_MAX:
        yield ("ERROR", "description", f"[{rid}] description > {DESC_MAX}")

    link = row.get("link", "")
    if link and not link.lower().startswith("https://"):
        yield ("ERROR", "link", f"[{rid}] link must be absolute https:// URL")
    img = row.get("image_link", "")
    if img and not img.lower().startswith(("http://", "https://")):
        yield ("ERROR", "image_link", f"[{rid}] image_link must be a URL")

    avail = row.get("availability", "").lower()
    norm = avail.replace("_", " ") if platform == "meta" else avail.replace(" ", "_")
    if avail and norm not in avail_set:
        yield ("ERROR", "availability",
               f"[{rid}] availability '{avail}' not in {sorted(avail_set)}")
    if norm in ("preorder", "backorder") and not row.get("availability_date"):
        yield ("WARN", "availability_date",
               f"[{rid}] {norm} needs availability_date (ISO 8601)")

    amount, cur = split_price(row, "price")
    if amount is not None and not price_ok(amount):
        yield ("ERROR", "price", f"[{rid}] price '{amount}' not numeric >= 0")
    if cur and len(cur) != 3:
        yield ("ERROR", "price", f"[{rid}] currency '{cur}' not ISO-4217 (3 letters)")
    if row.get("sale_price"):
        s_amt, _ = split_price(row, "sale_price")
        if s_amt and price_ok(s_amt) and amount and price_ok(amount) \
                and float(s_amt) >= float(amount):
            yield ("WARN", "sale_price",
                   f"[{rid}] sale_price not below price - will be ignored")

    cond = row.get("condition", "").lower()
    if cond and cond not in CONDITION:
        yield ("ERROR", "condition",
               f"[{rid}] condition '{cond}' not in {sorted(CONDITION)}")

    gtin, mpn, brand = row.get("gtin", ""), row.get("mpn", ""), row.get("brand", "")
    if gtin and not gtin_valid(gtin):
        yield ("ERROR", "gtin", f"[{rid}] gtin '{gtin}' fails GS1 check digit")
    if not gtin and not mpn:
        yield ("WARN", "gtin",
               f"[{rid}] no gtin and no mpn - add a unique product identifier")
    if not brand:
        yield ("WARN", "brand", f"[{rid}] brand missing (required for most items)")
    elif len(brand) > BRAND_MAX:
        yield ("ERROR", "brand", f"[{rid}] brand > {BRAND_MAX} chars")

    if len(row.get("product_type", "")) > PRODUCT_TYPE_MAX:
        yield ("ERROR", "product_type", f"[{rid}] product_type > {PRODUCT_TYPE_MAX}")
    if platform == "google" and not row.get("google_product_category"):
        yield ("INFO", "google_product_category",
               f"[{rid}] no google_product_category - Google will auto-assign")

    ag = row.get("age_group", "").lower()
    if ag and ag not in AGE_GROUP:
        yield ("ERROR", "age_group", f"[{rid}] age_group '{ag}' invalid")
    gd = row.get("gender", "").lower()
    if gd and gd not in GENDER:
        yield ("ERROR", "gender", f"[{rid}] gender '{gd}' invalid")

    if (row.get("color") or row.get("size")) and not row.get("item_group_id"):
        yield ("WARN", "item_group_id",
               f"[{rid}] variant attrs set but no item_group_id to group them")

    if platform == "meta":
        qty = row.get("quantity") or row.get("quantity_to_sell_on_facebook")
        if norm == "in stock" and qty == "0":
            yield ("WARN", "quantity",
                   f"[{rid}] in stock but quantity 0 - shop will show sold out")


def collect_issues(rows, platform):
    issues = []
    for row in rows:
        issues.extend(validate_row(row, platform))
    issues.sort(key=lambda t: SEVERITY_ORDER[t[0]])
    return issues


# --- diagnose --------------------------------------------------------------
# Map validation field -> the disapproval / policy reason a merchant sees.
DISAPPROVAL_MAP = {
    "image_link": "Image issues / invalid image (P1). Serve a live 500x500+ URL.",
    "link": "Landing page not crawlable / not HTTPS. Check robots + redirects.",
    "price": "Price mismatch (feed vs page) or bad currency. Match to the penny.",
    "availability": "Availability mismatch with microdata on the page.",
    "gtin": "Invalid GTIN / incorrect identifier. Fix check digit or omit.",
    "brand": "Missing brand / unidentifiable product.",
    "condition": "Missing or invalid condition.",
    "title": "Title policy: promo text, caps or too generic.",
    "google_product_category": "Category mismatch causing mis-serving.",
}


def diagnose(rows, platform):
    issues = collect_issues(rows, platform)
    buckets = {}
    for sev, field, msg in issues:
        if sev == "INFO":
            continue
        reason = DISAPPROVAL_MAP.get(field)
        if reason:
            buckets.setdefault(reason, {"count": 0, "example": msg})
            buckets[reason]["count"] += 1
    return issues, buckets


# --- build -----------------------------------------------------------------
def out_rows(rows, platform):
    """Normalise canonical rows into platform-shaped dicts."""
    out = []
    for r in rows:
        amount, cur = split_price(r, "price")
        price = f"{amount} {cur}" if amount else ""
        s_amt, s_cur = split_price(r, "sale_price")
        sale = f"{s_amt} {s_cur}" if s_amt else ""
        avail = r.get("availability", "").lower()
        if platform == "google":
            avail = avail.replace(" ", "_")
        else:
            avail = avail.replace("_", " ")
        o = {
            "id": r.get("id", ""), "title": r.get("title", ""),
            "description": r.get("description", ""), "link": r.get("link", ""),
            "image_link": r.get("image_link", ""),
            "availability": avail, "price": price, "sale_price": sale,
            "brand": r.get("brand", ""), "gtin": r.get("gtin", ""),
            "mpn": r.get("mpn", ""), "condition": r.get("condition", ""),
            "google_product_category": r.get("google_product_category", ""),
            "product_type": r.get("product_type", ""),
            "item_group_id": r.get("item_group_id", ""),
            "color": r.get("color", ""), "size": r.get("size", ""),
        }
        if platform == "meta":
            o["quantity_to_sell_on_facebook"] = (
                r.get("quantity") or r.get("quantity_to_sell_on_facebook") or "")
        out.append(o)
    return out


def build_xml(rows):
    """Google Merchant Center RSS 2.0 with the g: namespace."""
    ns = ("http://base.google.com/ns/1.0")
    items = []
    for o in out_rows(rows, "google"):
        parts = []
        for k, v in o.items():
            if not v:
                continue
            parts.append(f"      <g:{k}>{html.escape(v)}</g:{k}>")
        items.append("    <item>\n" + "\n".join(parts) + "\n    </item>")
    body = "\n".join(items)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<rss version="2.0" xmlns:g="{ns}">\n'
        "  <channel>\n"
        "    <title>Product feed</title>\n"
        f"    <description>Generated {datetime.utcnow().isoformat()}Z</description>\n"
        f"{body}\n"
        "  </channel>\n</rss>\n"
    )


def build_delimited(rows, platform, delim):
    shaped = out_rows(rows, platform)
    fields = list(shaped[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, delimiter=delim)
    w.writeheader()
    for o in shaped:
        w.writerow(o)
    return buf.getvalue()


# --- CLI -------------------------------------------------------------------
def cmd_validate(args):
    rows = load_products(args.file)
    issues = collect_issues(rows, args.platform)
    errs = sum(1 for i in issues if i[0] == "ERROR")
    if args.json:
        print(json.dumps({"products": len(rows), "errors": errs,
                          "issues": [{"severity": s, "field": f, "message": m}
                                     for s, f, m in issues]}, indent=2))
    else:
        for sev, field, msg in issues:
            print(f"{sev:5} {field:24} {msg}")
        print(f"\n{len(rows)} products - {errs} error(s), "
              f"{len(issues) - errs} warning/info")
    return 1 if errs else 0


def cmd_build(args):
    rows = load_products(args.file)
    if args.format == "xml":
        if args.platform != "google":
            sys.exit("xml is Google Merchant Center only; use csv/tsv for meta")
        content = build_xml(rows)
    elif args.format == "tsv":
        content = build_delimited(rows, args.platform, "\t")
    else:
        content = build_delimited(rows, args.platform, ",")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"wrote {args.out} ({len(rows)} products, {args.platform}/{args.format})")
    else:
        sys.stdout.write(content)
    return 0


def cmd_diagnose(args):
    rows = load_products(args.file)
    issues, buckets = diagnose(rows, args.platform)
    if args.json:
        print(json.dumps({"reasons": [
            {"reason": r, "count": d["count"], "example": d["example"]}
            for r, d in sorted(buckets.items(), key=lambda x: -x[1]["count"])
        ]}, indent=2))
        return 0
    if not buckets:
        print("No likely-disapproval patterns found. Feed looks clean.")
        return 0
    print("Likely disapproval reasons (most common first):\n")
    for reason, d in sorted(buckets.items(), key=lambda x: -x[1]["count"]):
        print(f"  x{d['count']:<3} {reason}")
        print(f"        e.g. {d['example']}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "build", "diagnose"):
        sp = sub.add_parser(name)
        sp.add_argument("file")
        sp.add_argument("--platform", choices=["google", "meta"], default="google")
        if name == "build":
            sp.add_argument("--format", choices=["xml", "tsv", "csv"], default="xml")
            sp.add_argument("-o", "--out")
        else:
            sp.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    return {"validate": cmd_validate, "build": cmd_build,
            "diagnose": cmd_diagnose}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
