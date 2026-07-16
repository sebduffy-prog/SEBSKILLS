---
name: incident-response-and-postmortem
category: devops
description: >-
  Run a live production incident and its blameless postmortem end to end. Use to
  classify severity (SEV1–SEV4), open a channel and assign the IC / Comms / Ops
  roles, keep a timestamped timeline, decide rollback vs roll-forward, run a
  stakeholder comms cadence, then write a blameless postmortem with a real
  root-cause analysis and owned, dated, tracked action items. Reach for this the
  moment something is on fire, paging, or degraded — or when a retro / RCA /
  five-whys / "write the postmortem" is asked for.
when_to_use:
  - A production outage or degradation is live and you need to run the response
  - Deciding severity, who is Incident Commander, and the comms cadence
  - Choosing rollback vs roll-forward and capturing a decision log
  - Writing a blameless postmortem / RCA after an incident is resolved
  - Turning a messy incident into owned, dated, tracked action items
when_not_to_use:
  - Routine bug triage with no user impact — use normal issue tracking
  - Setting up alerting/SLOs from scratch — that's an observability skill
  - Building CI/CD or deploy tooling — use github-actions-pipelines
  - A security breach requiring legal/forensics — escalate to your security-reviewer/IR team first
keywords:
  - incident-response
  - postmortem
  - blameless
  - sev1
  - severity
  - rca
  - root-cause
  - five-whys
  - incident-commander
  - rollback
  - runbook
  - oncall
  - pagerduty
  - sre
  - action-items
  - comms
similar_to:
  - dockerfile-and-compose-authoring
  - github-actions-pipelines
  - terraform-iac-modules
inputs_needed: What is broken and the observed user impact; who is on call / available; the deploy + rollback mechanism; where comms go (Slack/status page); a tracker for action items.
produces: A running incident with roles + timestamped timeline, a stakeholder comms cadence, a rollback/roll-forward decision, and a blameless postmortem with owned, dated action items.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Incident Response & Blameless Postmortem

Two jobs, in order: **(1) stop the bleeding**, then **(2) learn without blame.**
Grounded against Google's SRE Book (chapters "Managing Incidents" and "Postmortem
Culture") and PagerDuty's Incident Response docs. The core doctrine: **separate the
response roles**, keep **one shared source of truth**, and treat the postmortem as a
document about a **system that let a good person make a mistake** — never about the person.

## When to use

Something is degraded, paging, or on fire and a human must coordinate the fix — or
the fire is out and you owe a postmortem. If there is genuine user impact or you had
to page someone, run the full flow. If it's a quiet bug, skip this and use normal triage.

## Prerequisites

Honest dependencies — this skill is a **process**, not a binary:

- A real-time comms channel (Slack/Teams) and, ideally, a public **status page**.
- A tracker (GitHub Issues/Jira) so action items get IDs and owners.
- Knowledge of your **deploy + rollback** mechanism (the single most valuable thing
  to know during an incident). See github-actions-pipelines / use-railway.
- Optional: PagerDuty/Opsgenie for paging. The roles below work with or without them.

There is no CLI to install. The timeline and postmortem templates are inline below
(Steps 3 and 7) — copy and fill them; the judgement is yours.

## Step 1 — Declare and classify severity

Declaring early is cheap; under-declaring is expensive. **When in doubt, declare.**
Pick the severity from *observed impact*, not cause (cause is unknown yet).

| Sev  | Meaning                                             | Response                                   |
|------|-----------------------------------------------------|--------------------------------------------|
| SEV1 | Full outage / data loss / security. Revenue-critical| Page now. IC + full roster. Exec + status page. |
| SEV2 | Major feature down or severe degradation for many   | Page on-call. IC assigned. Status page.    |
| SEV3 | Partial/minor degradation, workaround exists        | Handle in hours. Channel, no full roster.  |
| SEV4 | Cosmetic / low impact, no urgency                   | Normal backlog. No incident process.       |

Write the declaration as one line in the channel:
`🔴 SEV2 declared — checkout latency p99 > 8s for ~30% of users since 14:02 UTC. IC: @you.`

## Step 2 — Assign roles (separate the hats)

The SRE Book's central lesson: **do not let one person both fix and coordinate.**
Assign explicitly, by name, even if one person wears two hats early on.

- **Incident Commander (IC)** — owns the incident, not the fix. Runs the room,
  delegates, holds the state. The IC's job is decisions and coordination.
- **Operations / Ops Lead** — the only role that touches production. Diagnoses,
  mitigates, executes the rollback. Reports findings to the IC.
- **Communications Lead** — owns external/stakeholder updates and the status page,
  so the Ops Lead is never interrupted by "any update?" pings.
- **Scribe** (optional but gold) — keeps the timestamped timeline live so the
  postmortem writes itself.

If you're solo: you are IC + Ops, and you **announce that** so others know to pick up
Comms. Hand off IC explicitly ("IC is now @sam") — never let it be ambiguous.

## Step 3 — Keep one live timeline (single source of truth)

Everything material gets a **UTC timestamp** in the channel: symptoms, hypotheses,
actions taken, and their effect. This is your future postmortem and your defence
against "wait, what did we already try?" Log actions *as you take them*.

```
14:02  First alert: checkout p99 latency > 8s (Datadog monitor #4412)
14:05  SEV2 declared. IC @you, Ops @sam, Comms @rae
14:09  Hypothesis: DB connection pool exhausted after 13:55 deploy (v482)
14:14  Ops: pool at 100/100 saturated — confirms hypothesis
14:17  DECISION: roll back v482 → v481 (roll-forward fix not ready)
14:21  Rollback complete, pool draining
14:26  p99 back under 800ms. Monitoring for 15 min before all-clear.
```

## Step 4 — Mitigate: rollback vs roll-forward

**Restore service first; find the true root cause later.** Mitigation ≠ resolution.

- **Roll back** when a recent deploy correlates with onset and the previous version
  is known-good. This is the default and usually fastest. Confirm the rollback
  target is actually deployable (migrations that aren't backward-compatible can make
  rollback unsafe — know this *before* the incident).
- **Roll forward** (hotfix) when there's no clean version to return to (e.g. a bad
  data migration, or the bug predates many merged changes). Slower, riskier — prefer
  rollback under time pressure.
- **Feature-flag / kill-switch** off the offending path when available — the fastest
  mitigation of all, and reversible.

Record the decision *and its rationale* in the timeline (line `14:17` above). A
decision with a "why" is worth ten without.

## Step 5 — Communicate on a cadence

Silence reads as "they don't know it's broken." The Comms Lead posts on a **fixed
interval** (SEV1: every ~30 min; SEV2: ~60 min) even when the update is "still
investigating, next update by HH:MM." Each update states: what's impacted, what
you're doing, and the **time of the next update.**

Status-page template:
```
[Investigating] 14:10 UTC — Some users may see slow or failing checkout.
We've identified a likely cause and are mitigating. Next update by 14:40 UTC.
[Monitoring]   14:26 UTC — A fix is applied and checkout has recovered.
We're monitoring to confirm. Next update by 14:45 UTC.
[Resolved]     14:45 UTC — Checkout is fully restored. A postmortem will follow.
```
Keep customer language blameless and jargon-free. Never speculate on root cause
publicly before it's confirmed.

## Step 6 — Resolve and hand off to postmortem

Declare all-clear only after metrics hold steady for a stated window (e.g. 15–30 min).
Then: assign a **postmortem owner** (usually the IC), set a due date (SEV1/2: within
~3–5 business days while memory is fresh), and drop the timeline into the doc.

## Step 7 — Write the blameless postmortem

**Blameless means:** assume everyone acted with good intent given the information they
had. Name systems and gaps, never people-as-culprits. "The deploy tool allowed a
config with no pool limit" — not "Sam forgot the limit." Blame kills reporting;
psychological safety is what makes incidents rare.

Required sections:

1. **Summary** — 2–3 sentences a stranger can understand. Impact + duration + cause.
2. **Impact** — who/what, how many users, how long, any SLO/error-budget burn, revenue.
3. **Timeline** — the UTC log from Step 3, lightly cleaned.
4. **Root cause analysis** — go past the proximate trigger. Use **Five Whys**:
   ```
   Why did checkout fail?      → DB connection pool was exhausted.
   Why was the pool exhausted? → v482 opened a connection per request, never pooled.
   Why did that ship?          → No load test caught it; unit tests passed.
   Why no load test?           → Checkout has no pre-prod load gate in CI.
   Why no gate?                → Never prioritised; no owner for perf regressions.
   ```
   The *real* fix lives at the bottom, not the top.
5. **What went well / what went poorly / where we got lucky** — the SRE Book's honest
   trio. "We got lucky the rollback target still worked" is a finding, not a comfort.
6. **Action items** — the whole point. See Step 8.

## Step 8 — Owned, dated, tracked action items

An action item that isn't in a tracker with an owner and a date **does not exist.**
Each must be a real ticket. Prefer prevention/detection over "be more careful."

| Action                                   | Type       | Owner | Due     | Ticket   |
|------------------------------------------|------------|-------|---------|----------|
| Add connection-pool ceiling + alert      | Prevent    | @sam  | 07-16   | OPS-1291 |
| Add load-test gate to checkout CI        | Prevent    | @rae  | 07-23   | OPS-1292 |
| Make rollback target check part of deploy| Mitigate   | @you  | 07-18   | OPS-1293 |
| Add pool-saturation dashboard + monitor  | Detect     | @sam  | 07-16   | OPS-1294 |

Good types: **Prevent, Detect, Mitigate, Process.** Avoid vague verbs ("investigate",
"look into") — they never get done. Assign a single **DRI** per item; shared
ownership is no ownership.

## Verify

You ran this well if all of these are true:

- [ ] Severity was declared in-channel with a timestamp and an IC named.
- [ ] IC and Ops were different hats (or the overlap was explicitly announced).
- [ ] A UTC timeline exists and the mitigation decision has a recorded rationale.
- [ ] Stakeholders got updates on a cadence, each naming the next update time.
- [ ] All-clear followed a stated monitoring window, not a hopeful guess.
- [ ] The postmortem is **blameless** (no person named as cause) and has a Five-Whys.
- [ ] Every action item has an owner, a due date, and a ticket ID.

## Pitfalls

- **Under-declaring to avoid noise.** Declaring is reversible and cheap; a silent
  SEV1 is a resignation letter. When unsure, go one level higher.
- **The fixer also coordinating.** The single most common failure. Split IC from Ops.
- **No comms = assumed dead.** Post "no news" updates; silence is worse than bad news.
- **Rollback assumed safe.** Non-backward-compatible migrations can make rollback
  destructive. Know your rollback safety *before* you need it.
- **Mitigation mistaken for resolution.** Service back ≠ cause understood. The
  postmortem still owes a root cause.
- **Blame leaking into the postmortem.** "X forgot to…" shuts down future honesty.
  Rewrite every such line as a system/tooling gap.
- **Action items with no owner/date.** They evaporate. The next identical incident is
  the receipt. One DRI, one due date, one ticket, always.
- **Postmortem written weeks later.** Memory decays fast — draft within days.
