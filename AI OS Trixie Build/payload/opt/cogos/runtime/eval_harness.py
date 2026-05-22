"""
eval_harness.py — Phase 0–3 verification suite for ship readiness.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from governance_invariant_engine import cogos_root


def _run_module(path: Path) -> Tuple[bool, str]:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if not spec or not spec.loader:
        return False, "load failed"
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            rc = mod.main()
            return rc == 0, f"exit {rc}"
        return True, "no main"
    except SystemExit as exc:
        return exc.code == 0, f"exit {exc.code}"
    except Exception as exc:
        return False, str(exc)


def run_eval_suite() -> Dict[str, Any]:
    root = cogos_root()
    runtime = root / "runtime"
    tests: List[Dict[str, Any]] = []

    try:
        from pattern_ledger import PatternLedger

        ledger = PatternLedger()
        if not ledger.verify_chain().get("ok"):
            ledger.repair_chain()
    except Exception:
        pass

    suites = [
        ("phase0_smoke", runtime / "phase0_smoke.py"),
        ("phase1_smoke", runtime / "phase1_smoke.py"),
        ("phase2_smoke", runtime / "phase2_smoke.py"),
        ("automatic_mode_smoke", runtime / "automatic_mode_smoke.py"),
        ("automatic_mode_v2_smoke", runtime / "automatic_mode_v2_smoke.py"),
        ("control_center_smoke", runtime / "control_center_smoke.py"),
        ("ul_stdlib_smoke", runtime / "ul_stdlib_smoke.py"),
        ("ul_stdlib_v02_smoke", runtime / "ul_stdlib_v02_smoke.py"),
        ("device_storage_smoke", runtime / "device_storage_smoke.py"),
        ("installer_smoke", runtime / "installer_smoke.py"),
        ("first_run_smoke", runtime / "first_run_smoke.py"),
        ("manifest_signing_smoke", runtime / "manifest_signing_smoke.py"),
        ("recovery_smoke", runtime / "recovery_smoke.py"),
        ("hardware_veto_smoke", runtime / "hardware_veto_smoke.py"),
        ("install_proof_smoke", runtime / "install_proof_smoke.py"),
        ("raid_proposal_smoke", runtime / "raid_proposal_smoke.py"),
        ("phaseB_shell_smoke", runtime / "phaseB_shell_smoke.py"),
        ("creative_providers_smoke", runtime / "creative_providers_smoke.py"),
        ("driver_policy_smoke", runtime / "driver_policy_smoke.py"),
        ("ul_package_smoke", runtime / "ul_package_smoke.py"),
        ("mesh_soak_smoke", runtime / "mesh_soak_smoke.py"),
        ("billing_hooks_smoke", runtime / "billing_hooks_smoke.py"),
        ("kernel_eval_smoke", runtime / "kernel_eval_smoke.py"),
        ("k32_semantic_smoke", runtime / "k32_semantic_smoke.py"),
        ("metal_proof_smoke", runtime / "metal_proof_smoke.py"),
        ("mesh_physical_smoke", runtime / "mesh_physical_smoke.py"),
        ("ul_app_bridge_smoke", runtime / "ul_app_bridge_smoke.py"),
        ("wine_wolf_bridge_smoke", runtime / "wine_wolf_bridge_smoke.py"),
        ("win_launcher_smoke", runtime / "win_launcher_smoke.py"),
    ]

    for name, path in suites:
        if path.exists():
            ok, detail = _run_module(path)
            tests.append({"name": name, "ok": ok, "detail": detail})
        else:
            tests.append({"name": name, "ok": False, "detail": "missing"})

    # Phase 3 inline checks
    p3: List[Tuple[str, Callable[[], bool]]] = []

    def _tiers():
        from compute_tiers import ComputeTierEngine

        e = ComputeTierEngine()
        assert e.check("nova.chat", profile_id="kid").allowed
        assert not e.check("ul.dangerous", profile_id="kid").allowed
        return True

    def _pkg():
        from cogos_pkg import install, list_packages, remove

        install("operator_notes", profile_id="operator")
        assert any(p["id"] == "operator_notes" and p["installed"] for p in list_packages())
        remove("operator_notes", profile_id="operator")
        return True

    def _backup():
        from cogos_backup import export_backup, list_backups

        r = export_backup("eval", profile_id="operator")
        assert r.get("ok") and list_backups()
        return True

    def _manifest():
        mf = root / "config" / "release_manifest.json"
        data = json.loads(mf.read_text(encoding="utf-8-sig"))
        return "3" in data.get("phases_complete", [])

    for name, fn in [("compute_tiers", _tiers), ("cogos_pkg", _pkg), ("cogos_backup", _backup), ("release_manifest", _manifest)]:
        try:
            ok = fn()
            tests.append({"name": f"phase3_{name}", "ok": ok, "detail": "ok" if ok else "assert failed"})
        except Exception as exc:
            tests.append({"name": f"phase3_{name}", "ok": False, "detail": str(exc)})

    passed = sum(1 for t in tests if t["ok"])
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": passed,
        "total": len(tests),
        "ok": passed == len(tests),
        "tests": tests,
    }
    out = root / "memory" / "logs" / "eval_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
