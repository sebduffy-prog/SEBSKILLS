---
name: consent-privacy-compliance
category: compliance
description: >-
  Audit and fix digital-advertising privacy compliance before non-consented tags
  stop serving. Use when configuring Google Consent Mode v2 (ad_storage,
  ad_user_data, ad_personalization, analytics_storage), an IAB TCF v2.3 CMP and
  Global Vendor List v3, running a tag/cookie audit, or drafting a GDPR/CCPA DPIA,
  records-of-processing, or data-retention schedule. Grounded on the real gtag and
  __tcfapi surfaces so every command, signal, and event name is correct.
when_to_use:
  - Setting up or debugging Google Consent Mode v2 (basic vs advanced) on a site or GTM container
  - Configuring a TCF v2.3 CMP, migrating from v2.2, or validating a TC string / disclosedVendors segment
  - Running a pre-launch tag and cookie audit to find pixels that fire before consent
  - Drafting a DPIA, ROPA (Article 30), or data-retention schedule for a campaign or martech stack
  - Answering "is our Google Ads / GA4 tracking still going to serve after the 2026 deadlines"
  - Mapping GDPR vs CCPA/CPRA obligations for a UK/EU/US ad campaign
when_not_to_use:
  - Building the CMP banner UI or general web components — use frontend-design
  - Writing GA4/GTM event tracking unrelated to consent — this skill only covers the consent layer
  - General app-security review (auth, secrets, injection) — use the security-review skill
  - Non-advertising data protection (HR, health records) — this is scoped to martech/adtech
keywords:
  - gdpr
  - ccpa
  - cpra
  - consent-mode-v2
  - iab-tcf
  - tcf-v2.3
  - cmp
  - global-vendor-list
  - tc-string
  - gtag
  - tcfapi
  - dpia
  - ropa
  - retention
  - tag-audit
  - cookie-audit
  - privacy
  - adtech
similar_to: []
inputs_needed: >-
  Site URL or GTM container export, list of ad/analytics vendors and pixels,
  target markets (EU/UK/US-state), and whether a CMP is already deployed.
produces: >-
  A consent-mode gtag config, a CMP/TCF configuration checklist, a tag-audit
  report of pre-consent fires, and filled DPIA / ROPA / retention templates.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Consent & Privacy Compliance (Consent Mode v2 + IAB TCF v2.3)

Get an advertising/analytics stack legally serving in the EU/UK and US. Two
mechanical layers break campaigns when misconfigured — **Google Consent Mode v2**
(how Google tags behave + what they tell Google's servers) and **IAB TCF v2.3**
(the consent string RTB partners read) — plus the paperwork (DPIA, ROPA,
retention) a data protection authority asks for.

## When to use

Reach for this whenever a client is about to launch tracking in a regulated
market, when GA4/Google Ads reporting suddenly shows "consent not granted", when
a CMP vendor asks you to migrate to TCF v2.3, or when legal requests a DPIA for a
new martech tool. The bar: after following this, tags fire in the correct order
against the correct signals and the documentation survives an audit.

## Prerequisites (honest deps)

- **No API keys required** for the audit/config work — it's HTML/JS + docs.
- A **Google-certified CMP** (Cookiebot, OneTrust, Usercentrics, CookieYes,
  Sourcepoint, etc.) if you need TCF v2.3 strings — you do **not** hand-roll a
  TC string; the CMP mints it. This skill configures and validates, not builds.
- `python3` (3.9 is fine) for the bundled tag-audit helper. No pip installs.
- To inspect a live page's tag order use the `claude-in-chrome` skill or
  DevTools → Network; this skill supplies the checklist, not a live crawler.
- **Grounding:** the Consent Mode v2 signals and `__tcfapi` surface below are the
  real ones (Google Tag Platform docs; IAB Tech Lab CMP API v2) — do not invent
  signal names.

## Recipe 1 — Google Consent Mode v2

Four v2 signals sit on top of the three original v1 ones. Each is `granted` or
`denied`.

| Signal | Layer | Effect |
|---|---|---|
| `ad_storage` | upstream | ad cookies / device IDs |
| `analytics_storage` | upstream | GA4 client_id / analytics cookies |
| `ad_user_data` (v2) | downstream | may user data be **sent** to Google for ads |
| `ad_personalization` (v2) | downstream | may data drive **remarketing** |

(Three v1 signals also exist — `functionality_storage`, `personalization_storage`,
`security_storage`.) `ad_storage` and `analytics_storage` gate whether the tag reads/writes on the
device. `ad_user_data` and `ad_personalization` do **not** change on-page
behaviour — they are flags Google's servers read to decide how the ping may be
used. All four must be present or Google Ads reporting degrades.

**Set the default BEFORE any Google tag loads** (deny-by-default for EU/UK):

```html
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied',
    'wait_for_update': 500,            // ms to wait for the CMP before firing
    'region': ['GB','ES','DE','FR']    // scope defaults to EU/UK; grant elsewhere
  });
</script>
<!-- gtag.js / GTM loads AFTER the block above -->
```

**Update when the user chooses** (called by the CMP's accept/reject handler):

```js
gtag('consent', 'update', {
  'ad_storage': 'granted',
  'ad_user_data': 'granted',
  'ad_personalization': 'granted',
  'analytics_storage': 'granted'
});
```

- **Basic** consent mode: Google tags are fully **blocked** until update →
  granted. No pings before consent.
- **Advanced** consent mode: tags load and send **cookieless pings** (with the
  consent state) even on deny, letting Google model conversions. This is the
  default recommendation for performance campaigns.
- In **GTM**, set the same defaults via a "Consent Initialization — All Pages"
  trigger + a Google tag configured for consent, or a certified CMP template.

## Recipe 2 — IAB TCF v2.3 CMP configuration

TCF is the RTB/programmatic consent layer. The CMP exposes a global
`__tcfapi()`; downstream vendors read the **TC string** it produces.

**2026 deadline (why this is urgent):** TCF **v2.3 with GVL v3** is the required
version; **v2.2 strings are treated as non-compliant** by Google and premium
demand from early 2026. A non-compliant/absent string means the ad request drops
to **Limited Ads** and CPMs collapse (often 60–80%). Two concrete v2.3 changes:
the **`disclosedVendors` segment is now mandatory** in the string (a bit per
vendor actually shown in the UI), and **GVL v3** replaces each purpose's
`descriptionLegal` with an `illustrations` array.

Config checklist for a certified CMP:

- [ ] CMP is on the IAB **CMP list** and set to emit **v2.3 / tcfPolicyVersion**.
- [ ] Loading the **latest GVL v3** (`vendor-list.json`), not a cached v2.2 list.
- [ ] All active RTB/SSP vendors selected in the vendor list; scan for vendors
      your ad tags call that are **missing** from the disclosed set.
- [ ] The 11 **Purposes** (1 store info … 11 personalised-ads measurement) and
      Special Features (1 precise geolocation, 2 device scan) are surfaced with
      correct legal-basis (consent vs legitimate interest) per your policy.
- [ ] Google is present as a vendor **and** Consent Mode is wired to TCF (Google's
      "Additional Consent" / AC string, if used).
- [ ] Banner blocks non-essential tags **until** `useractioncomplete`.

**Validate the TC string in the browser** (paste in DevTools console):

```js
// __tcfapi(command, version, callback, parameter)
__tcfapi('ping', 2, (d) => console.log('CMP:', d));
// PingReturn: cmpLoaded, cmpStatus, gdprApplies, apiVersion,
//             gvlVersion, tcfPolicyVersion, cmpId
__tcfapi('addEventListener', 2, (tcData, ok) => {
  if (!ok) return;
  // eventStatus: 'tcloaded' | 'cmpuishown' | 'useractioncomplete'
  console.log(tcData.eventStatus, tcData.tcString, tcData.purpose.consents);
});
```

Note: `getTCData` was **deprecated in v2.2** — use `addEventListener` to obtain
the string, not `getTCData`. Decode the string itself at
`iabtcf.com/#/decode` or with the `@iabtcf/core` decoder to confirm the
`disclosedVendors` segment is populated.

## Recipe 3 — Tag / cookie audit (find pre-consent fires)

The failure that stops tags serving and breaks the law is a pixel that fires
**before** the user consents. Run the bundled helper against a saved page or GTM
export to flag ordering problems and missing signals:

```bash
python3 scripts/tag_audit.py path/to/page.html
# or check a GTM container export:
python3 scripts/tag_audit.py path/to/GTM-XXXXXX_workspace.json
```

It reports: whether a `consent 'default'` block exists, whether all four v2
signals are set, whether a Google/analytics/ad tag appears **before** the
default block, and a list of known tracker hostnames it found. Then confirm live
in the browser: Network tab, reload with cache disabled, and check nothing hits
`google-analytics.com`, `googleads`, `facebook.com/tr`, `doubleclick`, etc.
before the CMP's accept event.

## Recipe 4 — DPIA / ROPA / retention templates

Fill these from the audit (copy into a doc; the docx skill can produce the
deliverable).

**DPIA** (GDPR Art. 35 — required for large-scale tracking / profiling, e.g.
behavioural profiling, cross-site tracking, or special-category targeting):
processing description → necessity & proportionality → risks to data subjects →
mitigations → residual risk → sign-off.

**ROPA** (Art. 30 record of processing): purpose · lawful basis (consent for
ad/analytics cookies under ePrivacy) · data categories · recipients/vendors ·
international transfers (SCCs for US SSPs) · **retention period** · security.

**Retention schedule** — set explicit TTLs and stop "keep forever":

| Data | Typical retention |
|---|---|
| GA4 user/event data | 2–14 months (set in GA4 Admin → Data Retention) |
| Ad-click / conversion IDs | campaign + attribution window, then delete |
| Consent records (TC string, timestamp) | proof-of-consent, ~1–5 yr |
| Raw log-level bid / conversion logs | days–weeks |

**GDPR vs CCPA/CPRA** quick map: GDPR = **opt-in** (deny by default, consent
before non-essential cookies). CCPA/CPRA = **opt-out** (allow, but honour "Do Not
Sell/Share" and **Global Privacy Control** signals; add a "Your Privacy Choices"
link). A site serving both runs the CMP geo-scoped: opt-in defaults for EU/UK `region`,
opt-out UI for California.

## Verify

- `gtag('consent','default',...)` appears **above** the gtag.js/GTM snippet in
  the HTML source. (`scripts/tag_audit.py` checks this.)
- All four v2 signals (`ad_storage`, `ad_user_data`, `ad_personalization`,
  `analytics_storage`) are present in both default and update calls.
- `__tcfapi('ping',2,…)` returns `cmpLoaded: true` and `tcfPolicyVersion` for
  v2.3; the decoded TC string has a non-empty `disclosedVendors` segment.
- GA4 DebugView / Tag Assistant shows consent granted only **after** the accept
  click; Network tab shows no tracker requests before it.
- DPIA, ROPA, and retention schedule exist and name every vendor the audit found.

## Pitfalls

- **Only setting `ad_storage`/`analytics_storage`.** Missing `ad_user_data` /
  `ad_personalization` is the #1 v2 error — Google Ads flags "consent not granted".
- **Default block placed after the tag.** If gtag.js loads first, the deny
  default never applies and cookies drop pre-consent — a GDPR breach and the
  exact thing the audit catches.
- **Shipping v2.2 TC strings past the 2026 cutover.** Treated as non-compliant →
  Limited Ads → CPM collapse. Confirm the CMP emits v2.3 + GVL v3.
- **Missing `disclosedVendors`.** A v2.3 string without it is invalid even if
  otherwise well-formed.
- **Relying on `getTCData`.** Deprecated in v2.2 — use `addEventListener`.
- **Hand-rolling a TC string.** Never — only a certified CMP may mint one.
- **Assuming CCPA = GDPR.** Opt-out vs opt-in are opposite defaults — a global
  deny-by-default banner over-suppresses US traffic; a US-style banner is illegal
  in the EU. Geo-scope it.
- **No retention TTL.** "Keep everything" fails Art. 5(1)(e); GA4 defaults to 2
  months unless you set it in Admin → Data Retention.
