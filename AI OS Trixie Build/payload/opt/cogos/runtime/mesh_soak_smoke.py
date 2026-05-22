"""Smoke: mesh family soak."""

from __future__ import annotations

from mesh_family_soak import run_soak


def main() -> int:
    report = run_soak(rounds=1)
    assert report["ok"], report
    assert report["peers"] == 3
    assert report["governance_bypass_blocked"]
    assert report["untrusted_peer_blocked"]
    print("mesh_soak_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
