"""Automatic Mode K-layer gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Set

from governance_invariant_engine import cogos_root
from ul.ul_intent_schema import KLayer, ULIntent


class AutoDecision:
    ALLOW = "allow"
    REVIEW = "review"
    REQUIRE_OPERATOR = "require_operator"
    SENTINEL = "sentinel"
    FORBID = "forbid"


def _load_cfg() -> dict:
    path = cogos_root() / "config" / "automatic_mode_k32.json"
    if not path.exists():
        return {
            "allow": list(range(1, 9)),
            "review": list(range(9, 17)),
            "require": list(range(17, 25)),
            "sentinel": [25],
            "forbid": list(range(26, 33)),
        }
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data.get("auto_mode", data)


_CFG = None


def _sets() -> tuple:
    global _CFG
    if _CFG is None:
        cfg = _load_cfg()
        _CFG = (
            set(cfg.get("allow", [])),
            set(cfg.get("review", [])),
            set(cfg.get("require", [])),
            set(cfg.get("sentinel", [])),
            set(cfg.get("forbid", [])),
        )
    return _CFG


def auto_decide(intent: ULIntent) -> str:
    allow, review, require, sentinel, forbid = _sets()
    k = intent.k_layer.value
    if k in forbid:
        return AutoDecision.FORBID
    if k in require:
        return AutoDecision.REQUIRE_OPERATOR
    if k in sentinel:
        return AutoDecision.SENTINEL
    if k in review:
        return AutoDecision.REVIEW
    if k in allow:
        return AutoDecision.ALLOW
    return AutoDecision.REVIEW


def gate_intent(intent: ULIntent, *, operator_present: bool = False) -> dict:
    decision = auto_decide(intent)
    allowed = decision in (AutoDecision.ALLOW, AutoDecision.REVIEW)
    if decision in (AutoDecision.REQUIRE_OPERATOR, AutoDecision.SENTINEL) and operator_present:
        allowed = True
    if decision == AutoDecision.FORBID:
        allowed = False
    return {
        "ok": allowed,
        "decision": decision,
        "k_layer": intent.k_layer.value,
        "operator_present": operator_present,
    }
