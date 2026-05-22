"""Smoke: kernel eval gate (deferred checklist)."""

from __future__ import annotations

from kernel_eval_gate import checklist_status


def main() -> int:
    st = checklist_status()
    assert st["ok"]
    assert st["status"] == "deferred"
    assert len(st["checklist"]) >= 4
    assert st["ready_for_kernel_eval"] is False
    print("kernel_eval_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
