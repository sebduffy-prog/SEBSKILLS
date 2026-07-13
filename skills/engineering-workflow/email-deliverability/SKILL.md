---
name: email-deliverability
category: engineering-workflow
description: >-
  Diagnose and fix why email lands in spam or gets rejected. Verify SPF, DKIM,
  and DMARC with dig; meet the 2024+ Gmail/Yahoo/Microsoft bulk-sender rules
  (DMARC + alignment, one-click List-Unsubscribe, <0.30% spam rate); parse
  aggregate DMARC XML reports; check blocklists; and review content for
  spam triggers. Use when mail hits junk, bounces with 5.7.x, DKIM fails, or a
  provider demands DMARC before a launch.
when_to_use:
  - Transactional or marketing email is landing in spam / junk instead of the inbox
  - Gmail or Yahoo started rejecting or rate-limiting your mail with 5.7.26 / bulk-sender errors
  - You need to set up or validate SPF, DKIM, and DMARC records for a sending domain
  - DMARC aggregate (rua) XML reports arrived and you need to read who is failing alignment
  - A campaign needs one-click List-Unsubscribe to comply with 2024+ sender rules
  - You suspect your sending IP or domain is on a blocklist (Spamhaus, Barracuda)
when_not_to_use:
  - Building an app that sends mail via an API — use the provider SDK (Postmark/SendGrid/SES) directly
  - Validating whether a recipient address is syntactically real — use python `email-validator`
  - Writing marketing copy or subject lines for engagement — this is a technical/compliance skill
  - Configuring an inbound mail server (Postfix/Dovecot receiving) — that is MTA administration
keywords:
  - spf
  - dkim
  - dmarc
  - deliverability
  - spam
  - list-unsubscribe
  - blocklist
  - dns
  - bulk-sender
  - alignment
  - postmaster
  - dig
  - rua
  - bounce
similar_to:
  - repo-context-packer
  - dependency-upgrade-migration
  - changelog-release-automation
inputs_needed: 'Sending domain (From: domain), a sample raw message with full headers, DMARC rua XML files if available'
produces: A prioritized fix list — DNS record edits (SPF/DKIM/DMARC), header additions, blocklist delisting steps, and content changes
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Email Deliverability

Diagnose why mail lands in spam or bounces, then produce the exact DNS, header,
and content fixes. Grounded against Gmail's bulk-sender guidelines (support.google.com/a/answer/81126),
RFC 7208 (SPF), RFC 6376 (DKIM), RFC 7489 (DMARC), and RFC 8058 (one-click unsubscribe).

## When to use

Mail hits junk, bounces with `550 5.7.x`, DKIM/SPF/DMARC shows `fail` in headers,
or a provider blocks a launch until DMARC exists. Work from evidence: pull the
raw headers and the live DNS, never guess.

## Prerequisites

- `dig` (bundled on macOS/Linux). No brew needed. Verify: `dig -v`.
- `python3` (3.9 on this Mac) for parsing DMARC XML — stdlib only, no pip installs.
- A **raw** message including full headers. In Gmail: open message → ⋮ → "Show original".
- Read access to the sending domain's DNS (to confirm what is actually published).
- Optional: DMARC aggregate reports (attached `.xml`, `.xml.gz`, or `.zip` from `rua=`).

The three pillars, in one line each:
- **SPF** — which IPs may send *for the envelope-from (Return-Path) domain* (RFC 7208).
- **DKIM** — a cryptographic signature tying the message to a domain via a public key in DNS (RFC 6376).
- **DMARC** — policy that requires SPF **or** DKIM to *pass AND align* with the visible `From:` domain, and tells receivers what to do on failure (RFC 7489).

## Recipe 1 — Inspect live authentication DNS

Replace `example.com` with the sending domain and `selector1` with the DKIM selector
(find it in a signed message's `DKIM-Signature:` header as `s=`).

```bash
DOMAIN=example.com
SELECTOR=selector1   # from the DKIM-Signature s= tag

# SPF — must be exactly ONE TXT starting v=spf1; ends in -all (hard) or ~all (soft)
dig +short TXT "$DOMAIN" | grep -i 'v=spf1'

# DKIM — public key for the selector
dig +short TXT "${SELECTOR}._domainkey.${DOMAIN}"

# DMARC — policy record at the _dmarc subdomain
dig +short TXT "_dmarc.${DOMAIN}"

# PTR / reverse DNS for the sending IP (bulk-sender requirement)
dig +short -x 203.0.113.25
```

Read the results:
- **SPF**: more than one `v=spf1` TXT = permanent SPF break (RFC 7208 forbids multiple).
  More than **10** DNS-lookup mechanisms (`include:`, `a`, `mx`, `redirect`) = `permerror`.
  Flatten nested includes if you are near the limit.
- **DKIM**: empty result means the selector is unpublished — signing is misconfigured.
- **DMARC**: absent = you fail the 2024 Gmail/Yahoo bulk rule outright.

A minimal valid, monitor-only DMARC record to start:

```
_dmarc.example.com. TXT "v=DMARC1; p=none; rua=mailto:dmarc@example.com; adkim=r; aspf=r; fo=1"
```

`p=none` satisfies Gmail's *bulk* baseline while you collect reports; tighten to
`p=quarantine` with a percentage ramp (`pct=25` → `pct=50` → `pct=100`), then
`p=reject`, once `rua` shows all legitimate sources aligning. The `p=` tag only
accepts `none`/`quarantine`/`reject`; the rollout percentage is the separate
`pct=` tag (RFC 7489 §6.3), never `p=100`.

## Recipe 2 — Read the Authentication-Results in a raw message

The receiving server records the verdict. Search the top headers of the raw message:

```bash
grep -iE 'authentication-results|received-spf|dkim-signature|arc-authentication' message.eml | head
```

You are looking for the receiver's line, e.g.:

```
Authentication-Results: mx.google.com;
   dkim=pass header.d=example.com;
   spf=pass (google.com: domain of bounce@example.com ...) smtp.mailfrom=bounce@example.com;
   dmarc=pass (p=NONE dis=NONE) header.from=example.com
```

Decision table:

| Symptom | Root cause | Fix |
|---|---|---|
| `dmarc=fail` but `spf=pass` | SPF **domain** (Return-Path) ≠ `From:` domain → no alignment | Sign with DKIM `d=` matching From, or align the Return-Path domain |
| `dkim=fail` (body hash) | Message body altered in transit (footer injection, list rewrite) | Sign after the modifying hop, or exclude volatile parts from `bh=` |
| `dkim=none` | No signature at all | Enable DKIM signing at the ESP/MTA |
| `spf=softfail`/`~all` + junked | Sending IP not in SPF, soft policy | Add the IP/`include:` to SPF, or rely on aligned DKIM |
| `dmarc=pass` but still spam | Reputation/content, not auth | Recipes 4 & 5 |

Alignment is the trap: SPF alignment checks the **Return-Path** domain, DKIM
alignment checks the **`d=`** domain. Either must equal the `From:` domain
(relaxed `r` = same org domain; strict `s` = exact match).

## Recipe 3 — Parse DMARC aggregate (rua) XML reports

Aggregate reports are gzipped XML sent daily by receivers. This stdlib script
summarizes pass/fail by source IP — no pip installs.

```bash
python3 - "$@" <<'PY' report1.xml report2.xml.gz
import sys, gzip, zipfile, io, collections
import xml.etree.ElementTree as ET

def load(path):
    if path.endswith('.gz'):
        return gzip.open(path, 'rb').read()
    if path.endswith('.zip'):
        z = zipfile.ZipFile(path)
        return z.read(z.namelist()[0])
    return open(path, 'rb').read()

rows = collections.Counter()
for path in sys.argv[1:]:
    root = ET.fromstring(load(path))
    org = root.findtext('report_metadata/org_name', '?')
    for rec in root.iter('record'):
        ip    = rec.findtext('row/source_ip', '?')
        count = int(rec.findtext('row/count', '0'))
        dkim  = rec.findtext('row/policy_evaluated/dkim', '?')
        spf   = rec.findtext('row/policy_evaluated/spf', '?')
        ok    = 'PASS' if (dkim == 'pass' or spf == 'pass') else 'FAIL'
        rows[(org, ip, dkim, spf, ok)] += count

print(f"{'source':18} {'ip':16} dkim spf  verdict  vol")
for (org, ip, dkim, spf, ok), n in rows.most_common():
    print(f"{org[:18]:18} {ip:16} {dkim:4} {spf:4} {ok:7} {n}")
PY
```

Every `FAIL` row is a sending source (an IP) that DMARC would block under
`p=reject`. Identify it (ESP, CRM, ticketing system), then either add it to SPF /
enable DKIM for it, or stop it spoofing your domain. Only move to `p=reject` when
the report is all `PASS` for known-good volume.

## Recipe 4 — One-click List-Unsubscribe (RFC 8058, required 2024+)

Marketing and subscribed bulk mail **must** carry both headers, and the POST
endpoint must unsubscribe without any further click or login:

```
List-Unsubscribe: <https://example.com/u/abc123>, <mailto:unsub@example.com?subject=unsub>
List-Unsubscribe-Post: List-Unsubscribe=One-Click
```

Rules that trip people up:
- `List-Unsubscribe-Post` value is the **literal** string `List-Unsubscribe=One-Click`.
- The HTTPS URL must accept an **HTTP POST** (Gmail/Yahoo POST it directly); a
  GET-only or confirmation-page URL fails the requirement.
- These headers must be inside the DKIM `h=` signed set, or the one-click is untrusted.
- Verify the endpoint honours POST:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X POST \
  -d 'List-Unsubscribe=One-Click' https://example.com/u/abc123
# expect 2xx, and the address actually suppressed
```

## Recipe 5 — Blocklists and content triggers

Blocklist lookup (Spamhaus Zen via DNS) for a sending IP `203.0.113.25` — reverse
the octets and query the zone; **any** A-record answer means listed:

```bash
IP=203.0.113.25
REV=$(echo "$IP" | awk -F. '{print $4"."$3"."$2"."$1}')
dig +short "${REV}.zen.spamhaus.org"       # 127.0.0.x = listed; empty = clean
dig +short "${REV}.b.barracudacentral.org"
```

If listed, use the operator's self-service delisting *after* fixing the root cause
(open relay, compromised account, snowshoe pattern); relisting is instant if the
cause remains. Note: Spamhaus public DNS blocks high-volume/commercial resolvers —
use your own resolver or their data feed for production checks.

Content/format triggers to review in the raw message:
- Missing or broken `text/plain` alternative in a `multipart/alternative` — send both parts.
- Link domain ≠ From domain, URL shorteners, or bare IP links.
- Big image, little text; single giant `<img>`; spammy ALL-CAPS subject with `!!!`/`$$$`.
- No physical mailing address in the footer (CAN-SPAM §5) for commercial mail.
- Sending-domain age/reputation cold-start — warm up volume gradually.

## Verify

Before declaring done:
1. `dig +short TXT _dmarc.$DOMAIN` returns exactly one `v=DMARC1` record.
2. A fresh test send to a Gmail account shows `dkim=pass ... dmarc=pass` in Show-original.
3. SPF has ≤10 lookups and a single `v=spf1` TXT.
4. Marketing sends carry both List-Unsubscribe headers and the POST endpoint returns 2xx.
5. Sending IP is clean on Spamhaus Zen.
6. Postmaster Tools spam rate < 0.30% (target < 0.10%).

## Pitfalls

- **SPF authenticates the Return-Path, not `From:`.** `spf=pass` with a mismatched
  bounce domain still yields `dmarc=fail`. Alignment is what DMARC judges.
- **Two SPF records = total SPF failure**, not a merge. Combine into one TXT.
- **`p=reject` before reading reports** silently drops legitimate mail from
  forgotten senders (CRM, invoicing, calendar). Always stage none → quarantine → reject.
- **DKIM key rotation** breaks signing if the new selector's public key isn't
  published *before* the private key goes live. Publish, wait for TTL, then switch.
- **Underscore-prefixed names are literal**: it is `_dmarc` and `_domainkey`, not
  `dmarc`/`domainkey`. A typo returns empty and looks like "no policy".
- **DNS caching** — a just-published record may not resolve until TTL expires;
  query the authoritative NS directly with `dig @ns1.example.com TXT _dmarc.example.com`.
- **Spamhaus over public resolvers (8.8.8.8/1.1.1.1) returns errors by policy**, not
  a clean result. Don't read a blank from a big resolver as "not listed".
