"""Smoke checks for the CoGOS Hardware Veto contract."""

from __future__ import annotations

from hardware_veto import HardwareVeto, REQUIRED_VETO_LINES


def main() -> int:
    veto = HardwareVeto()
    contract = veto.verify_contract()
    assert contract["ok"], contract
    status = veto.status()
    assert status["mode"] == "report_only", status
    assert set(status["physical_veto_lines"]).issuperset(REQUIRED_VETO_LINES), status
    assert status["authority"]["software_can_override"] is False
    event = veto.report_event("smoke_anomaly", "test", {"source": "hardware_veto_smoke"})
    assert event["ok"] and event["reported"]["software_action"] == "reported_only"
    proof = veto.write_proof()
    assert proof["ok"] and proof["proof_type"] == "hardware_veto_contract"
    print("hardware_veto_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
