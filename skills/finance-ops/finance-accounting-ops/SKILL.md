---
name: finance-accounting-ops
category: finance-ops
description: >-
  Run daily bookkeeping against Xero and QuickBooks Online: parse invoices and
  receipts into structured lines, reconcile bank statements to the ledger, build
  AP/AR aging, and push/pull records via the accounting APIs. Reach for this when
  someone says bank reconciliation, bookkeeping, invoice/receipt OCR, aged
  receivables/payables, chase overdue invoices, Xero sync, QuickBooks sync,
  realmId, xero-tenant-id, or close the month. Grounded on the real Xero
  Accounting API and QuickBooks Online v3 API with correct endpoints and OAuth.
when_to_use:
  - Reconciling a bank statement CSV against ledger or invoice records to find unmatched lines
  - Building AP/AR aging buckets (current, 1-30, 31-60, 61-90, 90+) to chase overdue invoices
  - Parsing supplier invoices or expense receipts (PDF/image) into date, total, tax, line items
  - Creating, approving, or querying invoices via Xero or QuickBooks Online APIs
  - Pulling AgedReceivables / AgedPayables reports straight from Xero or QBO
  - Wiring an OAuth2 connection to Xero (tenant) or QuickBooks (realmId) for a bookkeeping automation
when_not_to_use:
  - Marketing/media budget or MMX modelling and ROI forecasting (use mmm-lean or a marketing-science skill)
  - Building a general Stripe checkout or payments flow with no ledger sync (use a Stripe integration, not this)
  - Pure spreadsheet financial modelling with no live accounting API (use the xlsx skill)
  - Standing up an MCP server to expose these as Claude tools (use mcp-builder)
keywords:
  - bookkeeping
  - bank reconciliation
  - accounts receivable
  - accounts payable
  - aging report
  - invoice parsing
  - receipt ocr
  - xero api
  - quickbooks online
  - oauth2
  - realmid
  - xero-tenant-id
  - aged receivables
  - aged payables
  - ledger
  - month end close
similar_to: []
inputs_needed: Bank/ledger/invoice CSVs for offline work; for live sync, a Xero or QBO developer app (client id/secret), an OAuth2 access token, and the tenantId (Xero) or realmId (QBO)
produces: Reconciliation match reports, AP/AR aging buckets, parsed invoice/receipt line data, and create/query calls against the Xero or QuickBooks Online accounting API
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Finance & Accounting Ops

Daily bookkeeping glue: reconcile, age, parse, sync. The modelling side is
covered elsewhere — this is the boring-but-essential ledger work.

## When to use

A client or internal finance lead needs the books kept, not forecast: match the
bank feed, flag unpaid invoices, digitise a pile of receipts, or read/write
records in Xero or QuickBooks Online. Start offline with `scripts/reconcile.py`
(no keys, no network); reach for the APIs only when you must touch live data.

## Prerequisites

- **Offline path**: Python 3.9+ stdlib only. `scripts/reconcile.py` needs no
  packages and no network. Use it first — most reconciliation and aging work
  never needs an API.
- **Invoice/receipt parsing**: text PDFs → `pdfplumber` (`pip install pdfplumber`).
  Scanned images → Claude vision (pass the image to the model and ask for a
  strict JSON schema) or `pytesseract` if Tesseract is installed. There is no
  brew/Tesseract on this Mac by default — prefer the vision route.
- **Live sync** needs a developer app + OAuth2:
  - **Xero**: app at developer.xero.com. Scopes you usually want:
    `offline_access accounting.transactions accounting.contacts accounting.reports.read`.
  - **QuickBooks Online**: app at developer.intuit.com. Scope
    `com.intuit.quickbooks.accounting`. Test against the sandbox company first.
- Never hardcode client secrets or tokens. Read from env
  (`XERO_CLIENT_ID`, `QBO_ACCESS_TOKEN`, `QBO_REALM_ID`, …). Tokens are
  short-lived — refresh, don't paste.

## Recipes

### 1. Reconcile a bank statement (offline, no keys)

Export the bank feed and your ledger/invoices to CSV, then:

```bash
python3 scripts/reconcile.py match --bank bank.csv --ledger ledger.csv \
    --days 4 --out matches.csv
```

- `bank.csv`: `date, amount, description` (amount **signed**: +money in, −out).
- `ledger.csv`: `date, amount, reference`.
- Matcher is deterministic: exact amount to the cent + date within `--days`,
  greedy nearest-date first. It prints match count and both open lists, and
  writes matched pairs to `--out`. Nothing is mutated.

### 2. AP/AR aging (offline)

```bash
python3 scripts/reconcile.py aging --invoices invoices.csv --asof 2026-07-10
```

`invoices.csv`: `due_date, amount, paid[, contact]`. Only positive
`amount − paid` counts as outstanding. Buckets are measured from the **due
date**: `current` (≤0 days overdue), `1-30`, `31-60`, `61-90`, `90+`. Use the
`90+` figure to prioritise chasing.

### 3. Parse an invoice / receipt into structured lines

- **Text PDF**: `pdfplumber.open(path).pages[0].extract_text()` then pull the
  fields with regex, or feed the extracted text to the model asking for JSON:
  `{"supplier","invoice_no","date","currency","subtotal","tax","total","lines":[...]}`.
- **Photo/scan**: send the image to Claude vision and request that exact schema.
  Always echo `total == subtotal + tax` and reject if it fails — receipt OCR is
  the #1 source of silent errors.

### 4. Xero — read aged receivables, create an invoice

Base URL `https://api.xero.com/api.xro/2.0/`. Every call needs
`Authorization: Bearer <token>`, `Xero-tenant-id: <tenantId>`, and
`Accept: application/json`. Get `tenantId` once from
`GET https://api.xero.com/connections`.

```bash
# Aged receivables for one contact (Xero requires a contactId)
curl -s "https://api.xero.com/api.xro/2.0/Reports/AgedReceivablesByContact?contactId=$CID" \
  -H "Authorization: Bearer $XERO_TOKEN" \
  -H "Xero-tenant-id: $XERO_TENANT" -H "Accept: application/json"

# Create + approve an invoice (POST /Invoices, up to 50 per batch)
curl -s -X POST "https://api.xero.com/api.xro/2.0/Invoices" \
  -H "Authorization: Bearer $XERO_TOKEN" -H "Xero-tenant-id: $XERO_TENANT" \
  -H "Content-Type: application/json" -d '{
    "Type":"ACCREC","Status":"AUTHORISED",
    "Contact":{"ContactID":"'"$CID"'"},
    "LineItems":[{"Description":"Retainer July","Quantity":1,
                  "UnitAmount":2500,"AccountCode":"200"}],
    "DueDate":"2026-08-01"}'
```

OAuth2 token exchange/refresh is `POST https://identity.xero.com/connect/token`.
Aged payables is `Reports/AgedPayablesByContact` (same shape).

### 5. QuickBooks Online — query invoices, pull aging

Base URL production `https://quickbooks.api.intuit.com/v3/company/{realmId}/`,
sandbox `https://sandbox-quickbooks.api.intuit.com/v3/company/{realmId}/`.
Always append `?minorversion=75` (minor versions 1–74 were retired 1 Aug 2025).
Headers: `Authorization: Bearer <token>`, `Accept: application/json`.

```bash
QBO=https://sandbox-quickbooks.api.intuit.com/v3/company/$QBO_REALM_ID

# SQL-like query for open invoices
curl -s -G "$QBO/query" --data-urlencode \
  "query=SELECT * FROM Invoice WHERE Balance > '0' ORDER BY DueDate MAXRESULTS 100" \
  --data-urlencode "minorversion=75" -H "Authorization: Bearer $QBO_ACCESS_TOKEN" \
  -H "Accept: application/json"

# Aged receivables / payables reports
curl -s "$QBO/reports/AgedReceivables?minorversion=75" \
  -H "Authorization: Bearer $QBO_ACCESS_TOKEN" -H "Accept: application/json"
curl -s "$QBO/reports/AgedPayables?minorversion=75" \
  -H "Authorization: Bearer $QBO_ACCESS_TOKEN" -H "Accept: application/json"
```

Create an invoice: `POST $QBO/invoice?minorversion=75` with
`Content-Type: application/json` and a body containing `Line[]` (each with
`DetailType:"SalesItemLineDetail"`) and `CustomerRef`. Token endpoint is
`POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`.

## Verify

- `python3 -c "import ast; ast.parse(open('scripts/reconcile.py').read())"` → no error.
- Run the two offline commands on tiny fixtures and hand-check: matched count +
  unreconciled count must equal the bank-line count; aging buckets must sum to
  total outstanding.
- For any parsed invoice, assert `total == subtotal + tax` before you trust it.
- For live calls, first hit a read-only endpoint (`GET connections` / a report)
  and confirm 200 before any POST. Test QBO writes in the **sandbox** company.

## Pitfalls

- **Signed amounts.** The matcher keys on exact signed amount. If the bank feed
  has money-out as positive, normalise the sign first or nothing reconciles.
- **Xero aging needs a contactId.** There is no all-contacts aged report in the
  API — loop contacts, or use the report inside the ledger's own data.
- **QBO minorversion.** Omit it and you may silently get retired behaviour; pin
  `75` (or later) on every call.
- **Rate limits.** Xero: 60 calls/min and 5,000/day per tenant; both return
  `429` with `Retry-After` — honour it, don't hammer. QBO throttles per app too.
- **Token lifetime.** Xero access tokens last ~30 min; QBO ~1 hour. Refresh
  proactively; store the rotating refresh token, never a static one.
- **OCR trust.** Never post a parsed receipt straight to the ledger — subtotal +
  tax must equal total, and currency must be explicit, or a human reviews it.
- **Idempotency.** Re-running a create loop double-books. Key invoices on your
  own reference and check existence (`GET`/`query`) before `POST`.
