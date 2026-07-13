---
name: crm-pipeline-automation
category: sales-crm
description: >
  Read and write CRM records across HubSpot, Salesforce, and Pipedrive from the terminal —
  paginate contacts/deals, dedup by email/domain, enrich records, and snapshot pipeline value
  by stage. Reach for this whenever a task involves a CRM API, a private-app or OAuth token,
  SOQL/search queries, batch create/update, lead dedup, or exporting a deal pipeline to CSV.
  Grounded on the real HubSpot CRM v3 and Salesforce REST v60+ endpoints so every path,
  header, and rate limit is correct — not guessed.
when_to_use:
  - Pulling contacts, companies, or deals out of HubSpot / Salesforce / Pipedrive into CSV
  - Deduplicating leads or accounts by email, domain, or a custom key before an import
  - Snapshotting a sales pipeline (count + value per stage) for a report or dashboard
  - Batch creating or updating records after enrichment, with idempotent upserts
  - Writing a SOQL query or a HubSpot search filter and paginating past the result cap
  - Wiring a private-app token or OAuth client-credentials flow for a CRM integration
when_not_to_use:
  - Building a full email sequence / campaign send — that is a marketing-automation task, not CRM CRUD
  - Cleaning a plain spreadsheet with no CRM API involved — use the xlsx skill
  - General REST client scaffolding unrelated to a CRM — use mcp-builder or a plain HTTP client
  - Marketing-attribution or media-mix modelling — use the marketing-science skills
keywords:
  - hubspot
  - salesforce
  - pipedrive
  - crm
  - soql
  - pipeline
  - dedup
  - enrichment
  - private-app-token
  - oauth
  - batch-upsert
  - contacts
  - deals
  - rest-api
  - sales-ops
similar_to: []
inputs_needed: An API credential (HubSpot private-app token, Salesforce OAuth client id/secret + instance URL, or Pipedrive API token) and the object/pipeline to act on.
produces: CSV snapshots, dedup reports, and successful batch read/write calls against the CRM's REST API.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# CRM Pipeline Automation

Read-write automation for the three CRMs a VCCP account/new-business team actually touches:
**HubSpot**, **Salesforce**, and **Pipedrive**. Every endpoint below is real and current as of
July 2026. Default to read-only; gate every write behind an explicit confirmation and a dry run.

## When to use

Use this when a task names a CRM and an operation on records: export, dedup, enrich, upsert, or
pipeline snapshot. If the user only has a CSV and no API, this is the wrong skill (use `xlsx`).

## Prerequisites

- **HubSpot** — a **private-app access token** (starts `pat-`). Create it in the target account:
  Settings -> Integrations -> Private Apps, grant the CRM scopes you need
  (`crm.objects.contacts.read/write`, `crm.objects.deals.read/write`, etc.). Sent as
  `Authorization: Bearer pat-...`. Base URL `https://api.hubapi.com`.
- **Salesforce** — a **Connected App** for the OAuth 2.0 client-credentials or
  web-server flow, giving `client_id`, `client_secret`, and an instance/login URL
  (`https://login.salesforce.com` or your My Domain). You exchange these for an
  `access_token` + `instance_url`. Base path `/services/data/v60.0/` (latest is v67.0,
  Summer '26 — pin a version you have tested).
- **Pipedrive** — an **API token** (Settings -> Personal preferences -> API) OR OAuth. Token
  goes in the query string `?api_token=...`. Base `https://<company>.pipedrive.com/api/v1`
  (v2 exists for some resources).
- No Python packages required — the bundled helper uses only the standard library, so it runs on
  macOS system `python3` (3.9). `curl` and `jq` are handy for the manual recipes.
- **Never hardcode tokens.** Read from env (`HUBSPOT_TOKEN`, `SF_ACCESS_TOKEN`, `PIPEDRIVE_TOKEN`).

## Recipes

### 1. HubSpot — export, dedup, and pipeline snapshot (bundled helper)

```bash
export HUBSPOT_TOKEN=pat-xxxxxxxx
cd scripts

# Export every contact with chosen properties to CSV (auto-paginates):
python3 hubspot_snapshot.py dump contacts --props email,firstname,lastname,company --out contacts.csv

# Find contacts that share an email (normalised, case-insensitive):
python3 hubspot_snapshot.py dedup contacts --key email --out dupes.csv

# Snapshot deal count + total amount per stage for one pipeline:
python3 hubspot_snapshot.py pipeline --pipeline default --out snapshot.csv
```

The helper handles `429`/`5xx` with `Retry-After`-aware backoff and pages via `paging.next.after`.

### 2. HubSpot — search past the list endpoint (filters + the 10k cap)

The list endpoint returns everything unfiltered. To filter, POST to search (max 200/page,
**10,000 results total**, **5 req/s**). Page by feeding the last `id` back as a `>` filter
rather than climbing `after` past 10k.

```bash
curl -s -X POST https://api.hubapi.com/crm/v3/objects/deals/search \
  -H "Authorization: Bearer $HUBSPOT_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "filterGroups":[{"filters":[
      {"propertyName":"dealstage","operator":"EQ","value":"appointmentscheduled"},
      {"propertyName":"amount","operator":"GTE","value":"10000"}
    ]}],
    "properties":["dealname","amount","dealstage"],
    "sorts":[{"propertyName":"createdate","direction":"DESCENDING"}],
    "limit":200
  }' | jq '.results[] | {id, name:.properties.dealname, amount:.properties.amount}'
```

### 3. HubSpot — batch upsert (idempotent write)

Use `idProperty` to upsert on a unique key (e.g. `email`) so re-runs don't create duplicates.
Batch endpoints accept up to **100 records** per call.

```bash
curl -s -X POST https://api.hubapi.com/crm/v3/objects/contacts/batch/upsert \
  -H "Authorization: Bearer $HUBSPOT_TOKEN" -H "Content-Type: application/json" \
  -d '{"inputs":[
    {"idProperty":"email","id":"ada@vccp.com","properties":{"firstname":"Ada","jobtitle":"Planner"}}
  ]}' | jq '.status, .results[].id'
```

Other batch paths mirror this: `/batch/read`, `/batch/create`, `/batch/update`, `/batch/archive`.

### 4. Salesforce — token, SOQL query, and composite upsert

```bash
# a) Client-credentials token exchange -> access_token + instance_url
# Must hit your org's My Domain token endpoint — login.salesforce.com does NOT
# support client_credentials. My Domain is required, and the flow must be
# enabled on the Connected App (with a run-as user set).
curl -s https://<your-my-domain>.my.salesforce.com/services/oauth2/token \
  -d grant_type=client_credentials \
  -d client_id=$SF_CLIENT_ID -d client_secret=$SF_CLIENT_SECRET \
  | jq '{access_token, instance_url}'

export SF_ACCESS_TOKEN=... SF_INSTANCE=https://your-domain.my.salesforce.com

# b) SOQL query (URL-encode the SOQL; results paginate via nextRecordsUrl)
curl -s -G "$SF_INSTANCE/services/data/v60.0/query" \
  -H "Authorization: Bearer $SF_ACCESS_TOKEN" \
  --data-urlencode "q=SELECT Id,Name,Amount,StageName FROM Opportunity WHERE IsClosed=false ORDER BY Amount DESC" \
  | jq '.totalSize, .records[0]'

# Follow .nextRecordsUrl when .done == false:
curl -s "$SF_INSTANCE/services/data/v60.0/query/01g...-2000" -H "Authorization: Bearer $SF_ACCESS_TOKEN"

# c) Upsert on an external id field (idempotent) via PATCH:
curl -s -X PATCH "$SF_INSTANCE/services/data/v60.0/sobjects/Contact/External_Id__c/ABC123" \
  -H "Authorization: Bearer $SF_ACCESS_TOKEN" -H "Content-Type: application/json" \
  -d '{"LastName":"Lovelace","Title":"Planner"}'
```

For bulk writes use the **Composite** (`/composite/sobjects`, up to 200 records) or **Bulk API 2.0**
(`/jobs/ingest`, CSV upload) endpoints rather than a PATCH per record.

### 5. Pipedrive — deals by stage

```bash
curl -s "https://$COMPANY.pipedrive.com/api/v1/deals?status=open&limit=100&start=0&api_token=$PIPEDRIVE_TOKEN" \
  | jq '.data[] | {id, title, value, stage_id}'
# Page via .additional_data.pagination.next_start when more_items_in_collection is true.
```

### 6. Enrichment pattern (any CRM)

1. Export the records missing a field (recipe 1/2/4).
2. Join against your enrichment source (Clearbit, GWI, an internal table) **locally** — keep PII
   off third-party endpoints unless the DPA covers it.
3. Write back with the idempotent upsert (recipe 3/4c) keyed on email or an external id, so a
   partial re-run never duplicates.

## Verify

- Compile-check the helper: `python3 -c "import ast; ast.parse(open('scripts/hubspot_snapshot.py').read())"`.
- Dry-run auth: run any read recipe first; a `401` means a bad/expired token, `403` a missing scope.
- After a write, read the record back (recipe 2/4b) and confirm the field changed — don't trust the
  `200` alone.
- Confirm dedup output row counts against a `dump` total before deleting anything.

## Pitfalls

- **HubSpot v3 uses the `/crm/v3/objects/...` paths.** HubSpot has begun rolling out
  date-versioned paths (e.g. `/crm/objects/2026-03/...`); `v3` remains supported and is the safe
  default. If a `v3` call 404s on a new object type, check the object's documented version.
- **Search caps at 10,000 results and 5 req/s.** Past 10k, don't page `after` — filter by
  `createdate`/`id > lastSeen` and re-query. The helper's list endpoint has no 10k cap but can't filter.
- **Pin a Salesforce API version.** Endpoints and field behaviour differ across `v60` vs `v67`;
  don't let it float. Latest is v67.0 (Summer '26).
- **Amounts are strings in HubSpot.** `properties.amount` comes back as text — cast before summing
  (the helper does).
- **Rate limits differ per plan.** HubSpot burst is per-app-per-account; Salesforce has a 24h API
  call quota per org. Backoff on `429`, and batch instead of looping single calls.
- **Idempotency is on you.** Always upsert on a stable external key, never blind-create, or a rerun
  doubles your records — the exact mess this skill exists to clean up.
- **Secrets in env only.** No tokens in code, args that land in shell history, or committed files.
