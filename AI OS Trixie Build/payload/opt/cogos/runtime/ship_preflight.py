"""
ship_preflight.py - final CoGOS remaster readiness gate.

This is intentionally boring: gather the proofs that matter, fail closed when
any ship gate is missing, and write one report the operator can keep with the
ISO artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from eval_harness import run_eval_suite
from governance_invariant_engine import cogos_root
from operator_cockpit import full_cockpit
from pattern_ledger import PatternLedger
from manifest_signing import verify_core_manifests


REQUIRED_PATHS = [
    "bin/cognitive_init",
    "bin/cogos_boot.py",
    "bin/cogos_desktop.py",
    "bin/cogos_eval.py",
    "bin/cogos_pkg.py",
    "bin/cogos_backup.py",
    "bin/cogos_cockpit.py",
    "bin/cogos_ship.py",
    "bin/cogos_auto.py",
    "bin/cogos_ul_stdlib.py",
    "bin/cogos_ul_bridge.py",
    "bin/cogos-wine-bridge.py",
    "bin/wolf-wine",
    "config/wine_wolf_bridge.json",
    "runtime/wine_wolf_bridge/launcher.py",
    "runtime/wine_wolf_bridge_smoke.py",
    "docs/wine_wolf_bridge.md",
    "bin/cogos_device_storage.py",
    "bin/cogos_first_run.py",
    "bin/cogos_manifest.py",
    "bin/cogos_recovery.py",
    "bin/cogos_hardware_veto.py",
    "bin/cogos_install_proof.py",
    "runtime/cogos_runtime.py",
    "runtime/governance_invariant_engine.py",
    "runtime/pattern_ledger.py",
    "runtime/automatic_mode.py",
    "runtime/automatic_mode_smoke.py",
    "runtime/control_center_smoke.py",
    "runtime/ul/ul_stdlib.py",
    "runtime/ul/ul_stdlib_substrate.py",
    "runtime/ul_stdlib_smoke.py",
    "runtime/device_storage_manager.py",
    "runtime/device_storage_smoke.py",
    "runtime/installer_smoke.py",
    "runtime/first_run_wizard.py",
    "runtime/first_run_smoke.py",
    "runtime/manifest_signing.py",
    "runtime/manifest_signing_smoke.py",
    "runtime/recovery_mode.py",
    "runtime/recovery_smoke.py",
    "runtime/hardware_veto.py",
    "runtime/hardware_veto_smoke.py",
    "runtime/install_proof.py",
    "runtime/install_proof_smoke.py",
    "runtime/raid_proposal.py",
    "runtime/raid_proposal_smoke.py",
    "runtime/phaseB_shell_smoke.py",
    "runtime/creative_providers_smoke.py",
    "runtime/driver_policy_smoke.py",
    "runtime/creative_providers.py",
    "runtime/driver_policy.py",
    "runtime/files_api.py",
    "runtime/settings_api.py",
    "config/driver_policy.json",
    "shell/index.html",
    "bin/cogos_shell_window.py",
    "requirements-shell.txt",
    "runtime/eval_harness.py",
    "runtime/ship_preflight.py",
    "config/release_manifest.json",
    "config/compute_tiers.json",
    "config/package_catalog.json",
    "config/package_catalog.json.sig",
    "config/release_manifest.json.sig",
    "config/update_channel.json",
    "config/update_channel.json.sig",
    "config/trust_keys.json",
    "config/hardware_veto.json",
    "config/users.json",
    "docs/install_persistence.md",
    "docs/ul_stdlib_v0.1.md",
    "docs/device_storage_manager_mvp.md",
    "docs/first_run_wizard.md",
    "docs/signed_manifests.md",
    "docs/recovery_mode.md",
    "docs/hardware_veto.md",
    "docs/install_proof_metal.md",
    "docs/raid_proposal_mvp.md",
    "runtime/ul_app_bridge/bridge.py",
    "runtime/ul_app_bridge_smoke.py",
    "config/ul_app_bridge_policy.json",
    "docs/ul_app_bridge.md",
]

WRAPPER_PATHS = [
    "usr/local/bin/cogos-desktop-start",
    "usr/local/bin/cogos-hal-start",
    "usr/local/bin/cogos-cockpit",
    "usr/local/bin/cogos-eval",
    "usr/local/bin/cogos-pkg",
    "usr/local/bin/cogos-backup",
    "usr/local/bin/cogos-ship",
    "usr/local/bin/cogos-persist",
    "usr/local/bin/cogos-install",
    "usr/local/bin/cogos-auto",
    "usr/local/bin/cogos-ul-stdlib",
    "usr/local/bin/cogos-device-storage",
    "usr/local/bin/cogos-first-run",
    "usr/local/bin/cogos-manifest",
    "usr/local/bin/cogos-recovery",
    "usr/local/bin/cogos-hardware-veto",
    "usr/local/bin/cogos-install-proof",
    "usr/local/bin/cogos-shell-start",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _payload_root(root: Path) -> Path:
    # /payload/opt/cogos -> /payload
    if root.name == "cogos" and root.parent.name == "opt":
        return root.parent.parent
    return root


def _check_paths(root: Path, payload: Path, paths: Iterable[str]) -> Tuple[bool, list[Dict[str, Any]]]:
    rows: list[Dict[str, Any]] = []
    ok = True
    for rel in paths:
        base = root if rel.startswith(
            ("bin/", "runtime/", "config/", "law/", "memory/", "docs/", "shell/", "requirements-")
        ) else payload
        path = base / rel
        exists = path.exists()
        ok = ok and exists
        rows.append(
            {
                "path": str(path),
                "exists": exists,
                "bytes": path.stat().st_size if exists and path.is_file() else 0,
                "sha256": _sha256(path) if exists and path.is_file() else None,
            }
        )
    return ok, rows


def _release_manifest(root: Path) -> Dict[str, Any]:
    path = root / "config" / "release_manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"error": str(exc)}


def _boot_report(root: Path) -> Dict[str, Any]:
    path = root / "memory" / "logs" / "boot_report.json"
    if not path.exists():
        return {"ok": False, "reason": "missing boot_report.json"}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return {"ok": bool(data.get("ok")), "stage": data.get("stage"), "path": str(path), "report": data}
    except Exception as exc:
        return {"ok": False, "reason": str(exc), "path": str(path)}


def run_preflight() -> Dict[str, Any]:
    root = cogos_root()
    payload = _payload_root(root)
    logs = root / "memory" / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    eval_report = run_eval_suite()
    ledger_engine = PatternLedger()
    if not ledger_engine.verify_chain().get("ok"):
        ledger_engine.repair_chain()
    ledger = ledger_engine.verify_chain()
    cockpit = full_cockpit()
    release = _release_manifest(root)
    signed = verify_core_manifests(root)
    try:
        from hardware_veto import HardwareVeto

        hardware_veto = HardwareVeto(root).status()
    except Exception as exc:
        hardware_veto = {"ok": False, "error": str(exc)}
    required_ok, required = _check_paths(root, payload, REQUIRED_PATHS)
    wrappers_ok, wrappers = _check_paths(root, payload, WRAPPER_PATHS)
    boot = _boot_report(root)

    gates = [
        {"name": "phase_eval", "ok": bool(eval_report.get("ok")), "detail": f"{eval_report.get('passed')}/{eval_report.get('total')}"},
        {"name": "ledger_chain", "ok": bool(ledger.get("ok")), "detail": ledger},
        {"name": "required_payload", "ok": required_ok, "detail": "all present" if required_ok else "missing files"},
        {"name": "usr_local_wrappers", "ok": wrappers_ok, "detail": "all present" if wrappers_ok else "missing wrappers"},
        {
            "name": "release_manifest",
            "ok": bool({"3", "A", "B"} & set(release.get("phases_complete", []))),
            "detail": release.get("version", release),
        },
        {"name": "boot_report", "ok": bool(boot.get("ok")), "detail": boot.get("stage", boot.get("reason"))},
        {
            "name": "lawpulse_health",
            "ok": bool(cockpit.get("phase1", {}).get("law_pulse", {}).get("ledger_health", {}).get("ok")),
            "detail": cockpit.get("phase1", {}).get("law_pulse", {}).get("ledger_health", {}),
        },
        {"name": "signed_manifests", "ok": bool(signed.get("ok")), "detail": signed},
        {
            "name": "hardware_veto_contract",
            "ok": bool(hardware_veto.get("ok")),
            "detail": {
                "attached": hardware_veto.get("attached"),
                "deployment_ready": hardware_veto.get("deployment_ready"),
                "mode": hardware_veto.get("mode"),
            },
        },
    ]

    ok = all(g["ok"] for g in gates)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ok": ok,
        "status": "READY_TO_REMASTER" if ok else "HOLD_FOR_FIXES",
        "root": str(root),
        "payload_root": str(payload),
        "gates": gates,
        "eval": eval_report,
        "ledger": ledger,
        "release": release,
        "signed_manifests": signed,
        "hardware_veto": hardware_veto,
        "cockpit": cockpit,
        "boot_report": boot,
        "required": required,
        "wrappers": wrappers,
    }
    (logs / "ship_preflight.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def summary_lines(report: Dict[str, Any]) -> list[str]:
    lines = [f"CoGOS ship preflight: {report['status']}"]
    for gate in report["gates"]:
        mark = "PASS" if gate["ok"] else "FAIL"
        lines.append(f"{mark} {gate['name']}: {gate['detail']}")
    lines.append(f"Report: {cogos_root() / 'memory' / 'logs' / 'ship_preflight.json'}")
    return lines
