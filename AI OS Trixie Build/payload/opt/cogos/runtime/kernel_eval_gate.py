"""Kernel / alternate-base evaluation gate (Phase C — deferred scaffold)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from governance_invariant_engine import cogos_root


def checklist_status() -> Dict[str, Any]:
    path = cogos_root() / "config" / "kernel_eval_checklist.json"
    if not path.exists():
        return {"ok": False, "status": "missing", "error": "kernel_eval_checklist.json not found"}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        "ok": True,
        "status": data.get("status", "deferred"),
        "gate": data.get("gate", ""),
        "checklist": data.get("checklist", []),
        "next_base_candidates": data.get("next_base_candidates", []),
        "ready_for_kernel_eval": False,
    }
