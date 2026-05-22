"""Smoke: billing hooks metering."""

from __future__ import annotations

from billing_hooks import export_usage, reset_usage, status
from compute_tiers import ComputeTierEngine


def main() -> int:
    reset_usage()
    tiers = ComputeTierEngine()
    tiers.check("nova.chat", profile_id="operator")
    tiers.check("ul.dangerous", profile_id="kid")

    st = status()
    assert st["ok"]
    assert st["events_total"] >= 2

    exported = export_usage()
    assert exported["ok"]
    assert exported["count"] >= 2

    print("billing_hooks_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
