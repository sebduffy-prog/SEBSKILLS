---
name: paid-media-campaign-ops
category: adtech-ops
description: >
  Run the media-agency day-job from the terminal: create, list, pause, budget and report on Meta (Facebook/Instagram) ad campaigns with the official Meta Ads CLI (meta ads ...) or Marketing API v25, and mirror the same CRUD on Google Ads via the google-ads Python client. Use when the user says "launch a campaign", "change the budget", "pause the ad set", "pull last-7-day spend/ROAS", "closed-loop reporting", or wants safe budget/frequency guardrails before anything goes live. Ships a stdlib pre-flight guardrail so a fat-fingered budget or fatigued audience never reaches the platform.
when_to_use:
  - Creating, listing, pausing, activating or deleting Meta campaigns / ad sets / ads from the CLI or API
  - Changing a daily/lifetime budget or bid and wanting a cap + max-step guardrail first
  - Pulling closed-loop performance (spend, impressions, CTR, CPC, ROAS, frequency) for a date range
  - Scripting a cron job that reports daily spend across active campaigns
  - Doing the equivalent campaign CRUD on Google Ads with the google-ads Python client
  - Flagging ad-fatigue by checking average frequency against a ceiling before scaling
when_not_to_use:
  - Building a marketing MMM / spend-allocation model — use mmm-lean-rebuild or the strategy skills instead
  - Audience sizing, segmentation or TAM research — use the GWI Spark / SparkToro strategy skills instead
  - Designing the ad creative itself (image/video/copy) — use canvas-design, frontend-design or the media skills
  - Generic REST calls to an unrelated API — use a plain http/curl approach, not this ads-specific skill
keywords:
  - meta-ads
  - facebook-ads
  - marketing-api
  - google-ads
  - campaign-management
  - paid-media
  - budget-guardrail
  - frequency-cap
  - roas
  - insights
  - ad-set
  - closed-loop-reporting
  - ppc
  - ads-cli
  - adtech
similar_to: []
inputs_needed: Meta system-user ACCESS_TOKEN + AD_ACCOUNT_ID (act_...); optional google-ads.yaml (developer_token, OAuth client, refresh token, login_customer_id); campaign objective, budget in minor units, targeting, guardrail caps
produces: Live/paused campaigns, ad sets and ads; budget/status mutations; insights pulled as table/JSON/CSV; guardrail ALLOW/BLOCK verdicts (exit code) for CI
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Paid-Media Campaign Ops

API-driven campaign CRUD, budget/frequency guardrails, and closed-loop reporting for
Meta (Facebook/Instagram) and Google Ads — the literal media-agency day-job, driven
from the terminal so it is scriptable, auditable and safe.

## When to use

Reach for this whenever the request is "operate a live ad account": launch a campaign,
move a budget, pause an under-performer, or pull last week's spend/ROAS. The default
posture is **safe**: Meta's CLI creates everything PAUSED, mutations need an explicit
`--live`, and the bundled guardrail blocks reckless budget jumps and fatigued audiences
before they ship.

## Prerequisites

Honest dependencies — none are bundled, verify before promising a launch.

- **Meta Ads CLI** (official): `pip install meta-ads` — requires **Python 3.12+** (uv works too).
  The CLI is a thin wrapper over Marketing API **v25**. The `guardrail.py` helper in
  `scripts/` is separate and runs on the local Python 3.9.
- **Meta auth**: a *system user* token, not a personal one. Business Suite → Settings →
  Users → System Users → Generate New Token, granting scopes:
  `ads_management`, `business_management`, `read_insights`, `pages_show_list`,
  `pages_read_engagement`, `pages_manage_ads`, `catalog_management`.
  Export as env vars (never as CLI args — they leak into shell history):
  ```bash
  export ACCESS_TOKEN="EAAB..."       # system-user token
  export AD_ACCOUNT_ID="act_1234567890"
  meta auth status                     # confirm before doing anything
  ```
- **Google Ads** (optional): `pip install google-ads`, plus a `google-ads.yaml` with
  `developer_token`, `client_id`, `client_secret`, `refresh_token`, and
  `login_customer_id`. Requires an approved developer token.
- **Budgets are MINOR UNITS**: cents / pence. `--daily-budget 5000` = $50.00. Getting
  this wrong 100×s the spend — the guardrail's absolute cap is your seatbelt.

## Recipes

### 1. Inspect the account (always start here)

```bash
meta ads account                       # account name, currency, spend cap, status
meta ads campaign list --format table  # existing campaigns + ids
meta ads campaign list --format json   # machine-readable for scripting
```

### 2. Launch a campaign → ad set → ad (created PAUSED by default)

```bash
# Campaign — objective drives the whole delivery system. Budget in minor units.
meta ads campaign create \
  --name "Q3 Prospecting — UK" \
  --objective OUTCOME_SALES \
  --daily-budget 5000                  # £50.00/day

# Ad set — targeting + optimisation. Capture the CAMPAIGN_ID from the step above.
meta ads adset create CAMPAIGN_ID \
  --name "UK 25-44 Interest Stack" \
  --optimization-goal LINK_CLICKS \
  --billing-event IMPRESSIONS \
  --bid-amount 500 \
  --targeting-countries GB

# Ad — connect the ad set to a creative.
meta ads ad create ADSET_ID --name "Hero 4x5" --creative-id CREATIVE_ID
```

Everything lands PAUSED. Review, then flip live explicitly:

```bash
meta ads campaign update CAMPAIGN_ID --status ACTIVE
```

Bid-strategy nuance (Marketing API v25): `LOWEST_COST_WITHOUT_CAP` takes **no**
`bid_amount` (a supplied value is silently ignored); `LOWEST_COST_WITH_BID_CAP` and
`COST_CAP` **require** `bid_amount`. Pick deliberately.

### 3. Change a budget — guardrail FIRST, then `--live`

Never mutate a live budget blind. Pull the current figure, run the pre-flight check,
and only proceed on ALLOW (exit 0):

```bash
CUR=$(meta ads campaign list --format json | \
  python3 -c "import sys,json;print(next(c['daily_budget'] for c in json.load(sys.stdin)['data'] if c['id']=='CAMPAIGN_ID'))")

python3 scripts/guardrail.py budget \
  --current "$CUR" --proposed 7000 --cap 20000 --max-step-pct 20 \
  && meta ads budget CAMPAIGN_ID 7000 --live --yes
```

The guardrail BLOCKs (exit 1, `&&` short-circuits) if the new budget exceeds the
absolute cap or jumps more than the max single step — the two ways budgets blow up.

### 4. Frequency / fatigue guard before scaling

Ad fatigue shows up as rising frequency. Pull insights as JSON, gate on the ceiling:

```bash
meta ads insights get --campaign_id CAMPAIGN_ID \
  --fields impressions,reach,frequency,spend --date-preset last_7d \
  --format json > insights.json

python3 scripts/guardrail.py freq --insights insights.json --ceiling 3.0 \
  && echo "Fresh enough — safe to scale"
```

It reads `frequency` directly, or derives `impressions / reach` when absent, and BLOCKs
if any row breaches the ceiling. Refresh creative rather than pushing more budget into a
saturated audience.

### 5. Closed-loop reporting (the daily cron)

```bash
meta ads insights get \
  --fields spend,impressions,clicks,ctr,cpc,actions,purchase_roas \
  --date-preset last_7d --format json > report.json
```

Roll it up with the `xlsx` or `dataviz` skills for the client deck. For a scheduled
pull, wire this into the `schedule` skill or a plain cron entry; append `--no-input`
`--force` so it never blocks on a prompt.

### 6. Same CRUD on Google Ads (Python client)

```python
from google.ads.googleads.client import GoogleAdsClient
client = GoogleAdsClient.load_from_storage("google-ads.yaml")

# 1) Budget — amount_micros, 1_000_000 micros = 1 unit of account currency.
budget_svc = client.get_service("CampaignBudgetService")
op = client.get_type("CampaignBudgetOperation")
b = op.create
b.name = "Q3 Prospecting Budget"
b.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
b.amount_micros = 50_000_000                       # 50.00/day
budget_res = budget_svc.mutate_campaign_budgets(
    customer_id="1234567890", operations=[op])
budget_rn = budget_res.results[0].resource_name

# 2) Campaign — start PAUSED, mirror the Meta safe default.
camp_svc = client.get_service("CampaignService")
cop = client.get_type("CampaignOperation")
c = cop.create
c.name = "Q3 Prospecting — Search"
c.status = client.enums.CampaignStatusEnum.PAUSED
c.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
c.campaign_budget = budget_rn
c.manual_cpc.enhanced_cpc_enabled = True
camp_svc.mutate_campaigns(customer_id="1234567890", operations=[cop])
```

The same guardrail applies: `amount_micros` is micros, so validate with
`--current`/`--proposed` in micros and a micros `--cap`.

## Verify

- `meta auth status` → authenticated before any write.
- `python3 scripts/guardrail.py budget --current 5000 --proposed 5500 --cap 20000` → `ALLOW`, exit 0.
- `python3 scripts/guardrail.py budget --current 5000 --proposed 25000 --cap 20000` → `BLOCK`, exit 1.
- Dry-run a create before committing; confirm the object comes back PAUSED in `campaign list`.
- After a `--live` budget change, re-pull `campaign list --format json` and diff `daily_budget`.

## Pitfalls

- **Budget units.** Minor units on Meta (cents/pence), micros on Google. A $50 budget is
  `5000` vs `50000000`. Mixing them is the classic 100× / 1,000,000× overspend.
- **Personal token, not system user.** Personal tokens expire and lack `ads_management`
  at scale. Always mint a system-user token for automation.
- **Forgetting `--live`.** Meta CLI mutations (budget, uploads, bulk status) are dry by
  default; add `--live` (and `--yes`/`--no-input`/`--force` for unattended runs) or
  nothing happens. Conversely, never blanket-add `--live --yes` in a loop without the
  guardrail.
- **Bid strategy mismatch.** Passing `bid_amount` under `LOWEST_COST_WITHOUT_CAP` is
  silently ignored — you think you capped the bid and you did not.
- **Scaling into fatigue.** More budget on a high-frequency audience burns money; the
  freq guard exists so you refresh creative instead.
- **API version drift.** This targets Marketing API **v25** and google-ads current major.
  If a field 404s/deprecates, check the version in the CLI/library changelog before
  hand-patching request bodies.
- **Never hardcode tokens.** Env vars only; keep them out of shell history and the repo.
