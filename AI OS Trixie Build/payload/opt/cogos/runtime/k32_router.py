"""K32 runtime router — userspace semantic control plane."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from automatic_gate import AutoDecision, auto_decide, gate_intent
from governance_invariant_engine import cogos_root
from hal_device_schema import can_device_handle_intent, requires_operator_for_device
from hal_k32_registry import get_device
from k32_op_table import UnknownOpCode, resolve_op
from lawpulse_invariants import InvariantViolation, LawPulseContext, apply_lawpulse_invariants
from ul.ul_intent_schema import KLayer, ULIntent


@dataclass
class K32ExecutionContext:
    operator_present: bool = False
    profile_id: str = "operator"
    pid: int = 0
    escalations: list = field(default_factory=list)

    def escalate(self, reason: str) -> None:
        self.escalations.append(reason)


class K32RuntimeRouter:
    def __init__(self) -> None:
        self.root = cogos_root()
        self.log_path = self.root / "memory" / "traces" / "k32_calls.jsonl"

    def _log(self, row: Dict[str, Any]) -> None:
        row["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    def _build_intent_from_payload(self, k_layer: int, payload: Dict[str, Any]) -> Optional[ULIntent]:
        op_code = int(payload.get("op_code", 0))
        try:
            op = resolve_op(op_code)
        except UnknownOpCode:
            self._log({"event": "unknown_opcode", "op_code": op_code})
            return None
        layer = KLayer(k_layer) if 1 <= k_layer <= 32 else op["k_layer"]
        return ULIntent(
            name=f"{op['name_prefix']}:{op_code:#06x}",
            k_layer=layer,
            k_profile=[],
            k_profile_policy=op["k_profile_policy"],
            device_id=payload.get("device_id"),
            reversible_path=payload.get("reversible_path", True),
            coercive_perception=payload.get("coercive_perception", False),
        )

    def handle_k32_call(self, k_layer: int, payload: Dict[str, Any], context: K32ExecutionContext) -> Dict[str, Any]:
        if k_layer < 1 or k_layer > 32:
            return {"status": "einval", "errno": -22, "reason": "k_layer out of range"}

        intent = self._build_intent_from_payload(k_layer, payload)
        if intent is None:
            return {"status": "einval", "errno": -22, "reason": "unknown op_code"}

        decision = auto_decide(intent)
        lp_ctx = LawPulseContext(
            operator_present=context.operator_present,
            profile_id=context.profile_id,
        )

        if decision == AutoDecision.FORBID:
            self._log({"event": "forbid", "k_layer": k_layer, "intent": intent.name})
            return {"status": "eperm", "errno": -1, "decision": decision}

        if decision in (AutoDecision.REQUIRE_OPERATOR, AutoDecision.SENTINEL) and not context.operator_present:
            self._log({"event": "operator_required", "k_layer": k_layer, "decision": decision})
            return {"status": "eperm", "errno": -1, "decision": decision}

        gate = gate_intent(intent, operator_present=context.operator_present)
        if not gate["ok"]:
            return {"status": "eperm", "errno": -1, "gate": gate}

        device_id = payload.get("device_id")
        if device_id:
            device = get_device(str(device_id))
            if device:
                if not can_device_handle_intent(device, intent):
                    self._log({"event": "hal_ceiling", "device": device_id, "k_layer": k_layer})
                    return {"status": "device_forbidden", "errno": -1}
                if requires_operator_for_device(device, intent) and not context.operator_present:
                    return {"status": "eperm", "errno": -1, "reason": "device k_threshold"}
                try:
                    from driver_policy import DriverPolicyEngine

                    dev_row = device.raw or {"id": device_id}
                    pol = DriverPolicyEngine().evaluate_load(
                        dev_row,
                        profile_id=context.profile_id,
                        intent_k_layer=intent.k_layer.value,
                    )
                    if not pol.get("allowed"):
                        self._log({"event": "driver_policy_k_layer", "device": device_id, "policy": pol})
                        return {"status": "eperm", "errno": -1, "reason": "driver_policy intent_k_layer", "policy": pol}
                except Exception as exc:
                    self._log({"event": "driver_policy_error", "error": str(exc)})

        try:
            apply_lawpulse_invariants(intent, lp_ctx, None)
        except InvariantViolation as exc:
            self._log({"event": "invariant_violation", "reason": str(exc)})
            return {"status": "eperm", "errno": -1, "reason": str(exc)}

        if decision == AutoDecision.SENTINEL:
            context.escalate("MISALIGNMENT_SENTINEL")

        result = {"intent": intent.to_dict(), "gate": gate, "lawpulse_escalations": lp_ctx.escalations}
        self._log({"event": "ok", "k_layer": k_layer, "intent": intent.name, "decision": decision})
        return {"status": "ok", "errno": 0, "result": result, "decision": decision}

    def status(self) -> Dict[str, Any]:
        from lawpulse_invariants import lawpulse_status

        recent = []
        if self.log_path.exists():
            for line in self.log_path.read_text(encoding="utf-8").strip().splitlines()[-15:]:
                try:
                    recent.append(json.loads(line))
                except Exception:
                    continue
        return {"ok": True, "recent_calls": recent, "lawpulse": lawpulse_status()}
