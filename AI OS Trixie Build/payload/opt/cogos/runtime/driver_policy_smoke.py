"""Phase B.4: driver policy table smoke."""

from __future__ import annotations

from driver_policy import DriverPolicyEngine
from governance_invariant_engine import cogos_root


def main() -> int:
    root = cogos_root()
    assert (root / "config" / "driver_policy.json").exists()
    engine = DriverPolicyEngine()
    scan = engine.scan(profile_id="operator")
    assert scan["ok"] and scan.get("devices")
    assert scan.get("rules_count", 0) >= 5

    device = scan["devices"][0]
    ev = engine.evaluate_load(device, profile_id="operator", intent_k_layer=3)
    assert "allowed" in ev
    if ev.get("k_threshold"):
        ev_block = engine.evaluate_load(device, profile_id="kid", intent_k_layer=int(ev["k_threshold"]) + 1)
        assert ev_block.get("k_requires_operator") or not ev_block.get("allowed")

    if ev.get("requires_manual") and ev.get("rule_id"):
        approved = engine.approve(str(device.get("id")), str(ev["rule_id"]))
        assert approved["ok"]

    status = engine.status()
    assert status["ok"]
    print("driver_policy_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
