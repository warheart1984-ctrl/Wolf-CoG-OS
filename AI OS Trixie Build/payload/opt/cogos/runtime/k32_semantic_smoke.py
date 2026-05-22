"""K32 semantic plane integration smoke."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(ROOT / "runtime" / "ul"))

from automatic_gate import AutoDecision, auto_decide, gate_intent
from hal_device_schema import HALDevice, HALDevicePolicy, can_device_handle_intent
from hal_k32_registry import enrich_inventory_devices
from k32_op_table import resolve_op
from driver_policy import DriverPolicyEngine
from k32_forward_protocol import encode_request, decode_response
from k32_userspace_shim import cog_k32
from lawpulse_invariants import InvariantViolation, LawPulseContext, apply_lawpulse_invariants
from ul.ul_intent_schema import KLayer, KProfilePolicy, ULIntent, effective_k_class


def main() -> int:
    intent_p = ULIntent("observe", KLayer.K3)
    assert auto_decide(intent_p) == AutoDecision.ALLOW

    intent_a = ULIntent("agency", KLayer.K32, k_profile_policy=KProfilePolicy.EXPLICIT)
    assert auto_decide(intent_a) == AutoDecision.FORBID

    intent_sentinel = ULIntent("misalign", KLayer.K25)
    assert auto_decide(intent_sentinel) == AutoDecision.SENTINEL

    composite = ULIntent("attest-memory", KLayer.K11, k_profile=[KLayer.K28])
    assert effective_k_class(composite) == "A"

    dev = HALDevice("usb:cam", HALDevicePolicy("sensory_input", k_threshold=17, k_ceiling=24))
    assert can_device_handle_intent(dev, ULIntent("snap", KLayer.K20))
    assert not can_device_handle_intent(dev, ULIntent("agency", KLayer.K32))

    op = resolve_op(0x0001)
    assert op["k_layer"] == KLayer.K3

    ctx = LawPulseContext(operator_present=False)
    try:
        apply_lawpulse_invariants(ULIntent("id", KLayer.K29), ctx, None)
        raise AssertionError("agency without operator should fail")
    except InvariantViolation:
        pass

    assert cog_k32(3, {"op_code": 0x0001}) == 0
    assert cog_k32(32, {"op_code": 0x0501}, profile_id="kid") != 0

    op_throttle = resolve_op(0x0210)
    assert op_throttle["k_layer"] == KLayer.K20

    engine = DriverPolicyEngine()
    usb_dev = {"id": "sdb", "bus": "usb", "class": "storage"}
    ev_low = engine.evaluate_load(usb_dev, profile_id="operator", intent_k_layer=3)
    assert ev_low.get("allowed") is True
    assert not ev_low.get("k_requires_operator")
    ev_high = engine.evaluate_load(usb_dev, profile_id="kid", intent_k_layer=22)
    assert ev_high.get("allowed") is False
    assert ev_high.get("k_requires_operator") is True

    enriched = enrich_inventory_devices([{"class": "removable", "transport": "usb", "name": "sdb"}])
    assert enriched[0].get("k_threshold") is not None

    req = encode_request(3, {"op_code": 0x0001})
    assert len(req) > 8

    print("k32_semantic_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
