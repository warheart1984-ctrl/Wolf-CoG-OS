"""LawPulse K-class invariant enforcement."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root
from ul.ul_intent_schema import KLayer, ULIntent, effective_k_class, k_class_of


class InvariantViolation(Exception):
    pass


@dataclass
class LawPulseContext:
    operator_present: bool = False
    profile_id: str = "operator"
    escalations: List[str] = field(default_factory=list)

    def escalate(self, reason: str) -> None:
        self.escalations.append(reason)


def _trace_path() -> Path:
    return cogos_root() / "memory" / "traces" / "k32_lawpulse.jsonl"


def _log_event(kind: str, intent: ULIntent, context: LawPulseContext, extra: Optional[Dict[str, Any]] = None) -> None:
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": kind,
        "intent": intent.name,
        "k_layer": intent.k_layer.value,
        "effective_class": effective_k_class(intent),
        "profile_id": context.profile_id,
        "operator_present": context.operator_present,
    }
    if extra:
        row.update(extra)
    path = _trace_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def apply_lawpulse_invariants(intent: ULIntent, context: LawPulseContext, ledger: Any = None) -> None:
    k_class = effective_k_class(intent)
    if k_class == "P":
        _enforce_perception(intent, context, ledger)
    elif k_class == "R":
        _enforce_relation(intent, context, ledger)
    elif k_class == "D":
        _enforce_distortion(intent, context, ledger)
    elif k_class == "A":
        _enforce_agency(intent, context, ledger)
    else:
        raise InvariantViolation(f"Unknown K-class for {intent.k_layer.value}")


def _enforce_perception(intent: ULIntent, context: LawPulseContext, ledger: Any) -> None:
    if intent.extra.get("coercive_perception"):
        raise InvariantViolation("coercive perception not permitted")
    if intent.extra.get("hidden_saturation"):
        raise InvariantViolation("hidden saturation in perception path")
    _log_event("PERCEPTION_EVENT", intent, context)


def _enforce_relation(intent: ULIntent, context: LawPulseContext, ledger: Any) -> None:
    if intent.extra.get("forced_fixation"):
        raise InvariantViolation("forced fixation not permitted")
    if intent.extra.get("hidden_leverage"):
        raise InvariantViolation("hidden leverage in relational intent")
    _log_event("RELATION_EVENT", intent, context)


def _enforce_distortion(intent: ULIntent, context: LawPulseContext, ledger: Any) -> None:
    if intent.k_layer == KLayer.K25:
        _log_event("MISALIGNMENT_SENTINEL", intent, context)
        context.escalate("MISALIGNMENT_DETECTED")
        return
    if intent.extra.get("irreversible") and not context.operator_present:
        raise InvariantViolation("irreversible distortion without operator")
    _log_event("DISTORTION_EVENT", intent, context)


def _enforce_agency(intent: ULIntent, context: LawPulseContext, ledger: Any) -> None:
    if not context.operator_present:
        raise InvariantViolation("Agency-class intent without operator")
    if not intent.extra.get("reversible_path", True) and intent.k_layer.value >= 26:
        raise InvariantViolation("agency intent requires reversible_path")
    _log_event("AGENCY_EVENT", intent, context, {"reversible": intent.extra.get("reversible_path", True)})
    try:
        from pattern_ledger import PatternLedger
        from governance_invariant_engine import AuditRecord, Checkpoint

        PatternLedger().append_audit(
            AuditRecord(
                trace_id=f"k32-{intent.name}",
                module_id="LawPulse",
                lane_id="K32",
                subject=intent.name,
                passed=True,
                checkpoint=Checkpoint.OUTPUT_GATE,
                input_hash="",
                output_hash="",
                violations=[],
                drift_composite=0.0,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                stages_completed=["lawpulse.agency"],
            )
        )
    except Exception:
        pass


def lawpulse_status() -> Dict[str, Any]:
    path = _trace_path()
    recent: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").strip().splitlines()[-40:]:
            try:
                row = json.loads(line)
                recent.append(row)
                counts[row.get("kind", "?")] = counts.get(row.get("kind", "?"), 0) + 1
            except Exception:
                continue
    return {
        "ok": True,
        "k32_events": len(recent),
        "by_kind": counts,
        "recent": recent[-10:],
        "classes": {
            "P": "K1-K8",
            "R": "K9-K16",
            "D": "K17-K25",
            "A": "K26-K32",
        },
    }
