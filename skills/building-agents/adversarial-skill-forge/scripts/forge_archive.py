#!/usr/bin/env python3
"""Quality-diversity archive for adversarial-skill-forge.

Rainbow-Teaming MAP-Elites grid keyed by (attack_type x trigger_surface),
DGM keep-all lineage, ADAS novelty bonus. Pure inference-time bookkeeping:
the model writes attacks + scores them; this script only decides what enters
the archive, computes the breaker success rate, and exports the regression
eval set consumed by skill-creator's run_eval.py.

Immutable style: every operation returns a NEW archive dict; nothing mutates
the input. Usage:
  forge_archive.py insert   archive.json attacks.json  > archive.next.json
  forge_archive.py rate     archive.json attacks.json          # -> stdout float
  forge_archive.py evalset  archive.json                > gauntlet.json
"""
from __future__ import annotations
import argparse, copy, json, sys
from pathlib import Path

ATTACK_TYPES = ("false-positive-trigger", "false-negative-trigger",
                "body-step-failure", "scope-boundary", "ambiguity")
TRIGGER_SURFACES = ("description-verb", "sibling-keyword-overlap",
                    "when-not-to-use-boundary", "domain-noun", "task-phrasing")
NOVELTY_WEIGHT = 0.35  # ADAS: reward exploring unfilled/distant cells


def cell_key(attack: dict) -> str:
    return f"{attack['attack_type']}::{attack['trigger_surface']}"


def _validate(attack: dict) -> None:
    for f in ("id", "attack_type", "trigger_surface", "query", "broke", "severity"):
        if f not in attack:
            raise ValueError(f"attack missing field '{f}': {attack.get('id', attack)}")
    if attack["attack_type"] not in ATTACK_TYPES:
        raise ValueError(f"bad attack_type {attack['attack_type']!r}")
    if attack["trigger_surface"] not in TRIGGER_SURFACES:
        raise ValueError(f"bad trigger_surface {attack['trigger_surface']!r}")


def _fitness(attack: dict, archive: dict) -> float:
    """Successful + severe + novel scores highest. Novelty = empty cell bonus."""
    if not attack["broke"]:
        return 0.0
    novelty = NOVELTY_WEIGHT if cell_key(attack) not in archive["cells"] else 0.0
    return float(attack["severity"]) + novelty


def insert(archive: dict, attacks: list[dict]) -> dict:
    """Return a NEW archive: elites replaced when a fitter attack wins a cell.
    Keep-all lineage (DGM): every scored attack is appended to `lineage`,
    so the gauntlet only ever grows and old attacks stay as regression cases."""
    nxt = copy.deepcopy(archive)
    for atk in attacks:
        _validate(atk)
        nxt["lineage"].append(atk)
        if not atk["broke"]:
            continue  # defended attacks stay in lineage as regression cases only
        key = cell_key(atk)
        incumbent = nxt["cells"].get(key)
        if incumbent is None or _fitness(atk, archive) > _fitness(incumbent, archive):
            nxt["cells"][key] = atk
    nxt["rounds"] = archive.get("rounds", 0) + 1
    return nxt


def breaker_success_rate(attacks: list[dict]) -> float:
    """Fraction of this round's attacks that broke the candidate skill."""
    if not attacks:
        return 0.0
    return sum(1 for a in attacks if a["broke"]) / len(attacks)


def to_evalset(archive: dict) -> list[dict]:
    """Export the keep-all lineage as run_eval.py's format. Trigger attacks map
    to {query, should_trigger}; false-positive attacks must NOT trigger,
    false-negative attacks MUST trigger. Body attacks carry expectations for
    the grader agent."""
    seen, out = set(), []
    for atk in archive["lineage"]:
        if atk["id"] in seen:
            continue
        seen.add(atk["id"])
        row = {"query": atk["query"], "id": atk["id"],
               "attack_type": atk["attack_type"],
               "trigger_surface": atk["trigger_surface"]}
        if atk["attack_type"] == "false-positive-trigger":
            row["should_trigger"] = False
        elif atk["attack_type"] in ("false-negative-trigger", "scope-boundary", "ambiguity"):
            row["should_trigger"] = True
        else:  # body-step-failure -> graded, not a trigger test
            row["should_trigger"] = True
            row["expectations"] = atk.get("expectations", [])
        out.append(row)
    return out


def empty_archive() -> dict:
    return {"cells": {}, "lineage": [], "rounds": 0}


def _load(p: str) -> dict:
    return json.loads(Path(p).read_text()) if p != "-" else json.load(sys.stdin)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("insert", "rate", "evalset", "init"))
    ap.add_argument("archive", nargs="?")
    ap.add_argument("attacks", nargs="?")
    a = ap.parse_args()
    if a.cmd == "init":
        print(json.dumps(empty_archive(), indent=2)); return 0
    archive = _load(a.archive)
    if a.cmd == "insert":
        print(json.dumps(insert(archive, _load(a.attacks)), indent=2))
    elif a.cmd == "rate":
        print(breaker_success_rate(_load(a.attacks)))
    elif a.cmd == "evalset":
        print(json.dumps(to_evalset(archive), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
