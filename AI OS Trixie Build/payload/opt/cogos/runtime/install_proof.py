"""
install_proof.py — Phase A.1 install + persistence proof bundle.

Collects plan/validate/proof artifacts and post-install checks into one operator
bundle suitable for archiving beside the ISO (real hardware or lab VM).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _installer_cmd() -> Optional[Path]:
    for candidate in (
        Path("/usr/local/bin/cogos-install"),
        cogos_root().parent.parent / "usr" / "local" / "bin" / "cogos-install",
    ):
        if candidate.exists():
            return candidate
    return None


def _persist_cmd() -> Optional[Path]:
    for candidate in (
        Path("/usr/local/bin/cogos-persist"),
        cogos_root().parent.parent / "usr" / "local" / "bin" / "cogos-persist",
    ):
        if candidate.exists():
            return candidate
    return None


def _run_json(cmd: List[str], timeout: int = 20) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        stdout = completed.stdout.strip()
        if stdout.startswith("{"):
            data = json.loads(stdout)
            if isinstance(data, dict):
                data.setdefault("returncode", completed.returncode)
                data["stderr"] = completed.stderr.strip()
                return data
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


METAL_CHECKLIST: List[Dict[str, str]] = [
    {"id": "live_boot", "label": "Live ISO boots to desktop", "kind": "manual"},
    {"id": "install_plan", "label": "cogos-install plan --target /dev/sdX --json", "kind": "auto"},
    {"id": "install_validate", "label": "cogos-install validate --target /dev/sdX --json", "kind": "auto"},
    {"id": "install_apply", "label": "cogos-install apply (lab disk only)", "kind": "manual"},
    {"id": "reboot_installed", "label": "Reboot from installed disk", "kind": "manual"},
    {"id": "persist_status", "label": "cogos-persist status shows COGOSDATA mounted", "kind": "auto"},
    {"id": "pid1_proof", "label": "cogos-pid1-proof / pid1_proof.json", "kind": "auto"},
    {"id": "eval_run", "label": "cogos-eval run — all tests pass", "kind": "auto"},
    {"id": "desktop", "label": "cogos-desktop-start — Control Center loads", "kind": "manual"},
    {"id": "backup_export", "label": "cogos-backup export on installed system", "kind": "manual"},
]


class InstallProofCollector:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or cogos_root()
        self.log_dir = self.root / "memory" / "logs"
        self.bundle_dir = self.log_dir / "install_proof_bundles"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.bundle_dir.mkdir(parents=True, exist_ok=True)

    def _install_paths(self) -> Dict[str, Path]:
        return {
            "install_log": self.log_dir / "install.log",
            "install_proof": self.log_dir / "install_proof.json",
            "boot_report": self.log_dir / "boot_report.json",
            "pid1_proof": self.log_dir / "pid1_proof.json",
            "eval_report": self.log_dir / "eval_report.json",
            "ship_preflight": self.log_dir / "ship_preflight.json",
            "runtime_proof": self.log_dir / "runtime_proof.json",
        }

    def install_plan(self, target: str) -> Dict[str, Any]:
        target = target.strip()
        installer = _installer_cmd()
        if not installer:
            return {"ok": False, "error": "cogos-install not found", "target": target}
        return _run_json(["sh", str(installer), "plan", "--target", target, "--json"])

    def install_validate(self, target: str) -> Dict[str, Any]:
        target = target.strip()
        installer = _installer_cmd()
        if not installer:
            return {"ok": False, "error": "cogos-install not found", "target": target}
        return _run_json(["sh", str(installer), "validate", "--target", target, "--json"])

    def install_proof_read(self) -> Dict[str, Any]:
        installer = _installer_cmd()
        path = self._install_paths()["install_proof"]
        if installer and os.name != "nt":
            out = _run_json(["sh", str(installer), "proof", "--json"])
            if out.get("ok") is not False or "status" in out:
                return out
        if path.exists():
            data = _read_json(path, {})
            return {"ok": True, "source": "memory/logs/install_proof.json", **data}
        return {"ok": False, "reason": "no install proof yet", "path": str(path)}

    def persistence_status(self) -> Dict[str, Any]:
        persist = _persist_cmd()
        if persist:
            out = _run_json([str(persist), "status"])
            if out:
                return out
        return {
            "ok": True,
            "label": "COGOSDATA",
            "mounted": False,
            "note": "cogos-persist unavailable on this host",
        }

    def auto_checks(self, *, target: str = "", skip_eval: bool = False) -> Dict[str, Any]:
        checks: Dict[str, Any] = {}
        paths = self._install_paths()

        if target:
            checks["install_plan"] = self.install_plan(target)
            checks["install_validate"] = self.install_validate(target)
        else:
            checks["install_plan"] = {"ok": None, "skipped": "no --target"}
            checks["install_validate"] = {"ok": None, "skipped": "no --target"}

        checks["install_proof"] = self.install_proof_read()
        checks["persistence"] = self.persistence_status()

        for key in ("boot_report", "pid1_proof", "eval_report", "ship_preflight", "runtime_proof"):
            p = paths[key]
            data = _read_json(p)
            checks[key] = {
                "ok": bool(data) and (data.get("ok", True) if isinstance(data, dict) else True),
                "path": str(p),
                "exists": p.exists(),
                "summary": data if isinstance(data, dict) else {"present": bool(data)},
            }

        if skip_eval:
            checks["eval_live"] = {"ok": None, "skipped": "use cogos-eval run on metal"}
        else:
            try:
                from eval_harness import run_eval_suite

                eval_report = run_eval_suite()
                checks["eval_live"] = {
                    "ok": bool(eval_report.get("ok")),
                    "passed": eval_report.get("passed"),
                    "total": eval_report.get("total"),
                }
            except Exception as exc:
                checks["eval_live"] = {"ok": False, "error": str(exc)}

        return checks

    def build_checklist(self, checks: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for item in METAL_CHECKLIST:
            row = dict(item)
            cid = item["id"]
            if cid == "install_plan":
                row["passed"] = bool(checks.get("install_plan", {}).get("ok"))
            elif cid == "install_validate":
                row["passed"] = bool(checks.get("install_validate", {}).get("ok"))
            elif cid == "persist_status":
                ps = checks.get("persistence", {})
                row["passed"] = bool(ps.get("mounted") or ps.get("config_bound"))
            elif cid == "pid1_proof":
                row["passed"] = bool(checks.get("pid1_proof", {}).get("exists")) and bool(
                    checks.get("pid1_proof", {}).get("summary", {}).get("pid1_gate_ok", checks.get("pid1_proof", {}).get("ok"))
                )
            elif cid == "eval_run":
                row["passed"] = bool(checks.get("eval_live", {}).get("ok") or checks.get("eval_report", {}).get("ok"))
            elif item["kind"] == "manual":
                row["passed"] = None
            else:
                row["passed"] = None
            rows.append(row)
        return rows

    def capture_bundle(
        self,
        *,
        target: str = "",
        output_dir: Optional[Path] = None,
        label: str = "capture",
    ) -> Dict[str, Any]:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out_dir = output_dir or (self.bundle_dir / f"{label}-{stamp}")
        out_dir.mkdir(parents=True, exist_ok=True)

        checks = self.auto_checks(target=target, skip_eval=True)
        checklist = self.build_checklist(checks)
        auto_passed = sum(1 for r in checklist if r.get("passed") is True)
        auto_total = sum(1 for r in checklist if r.get("kind") == "auto")

        bundle: Dict[str, Any] = {
            "ok": True,
            "timestamp": utc_now(),
            "label": label,
            "target": target or None,
            "root": str(self.root),
            "output_dir": str(out_dir),
            "checklist": checklist,
            "checks": checks,
            "auto_passed": auto_passed,
            "auto_total": auto_total,
            "metal_ready": auto_passed == auto_total and bool(checks.get("install_proof", {}).get("ok")),
            "note": "metal_ready requires install_proof.json from a completed apply on real hardware",
        }

        copied: List[str] = []
        for name, path in self._install_paths().items():
            if path.exists():
                dest = out_dir / path.name
                shutil.copy2(path, dest)
                copied.append(name)

        bundle_path = out_dir / "install_proof_bundle.json"
        bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        bundle["bundle_path"] = str(bundle_path)
        bundle["copied_artifacts"] = copied

        latest = self.log_dir / "install_proof_bundle.json"
        latest.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return bundle

    def verify_bundle(self, bundle_path: Optional[Path] = None) -> Dict[str, Any]:
        path = bundle_path or (self.log_dir / "install_proof_bundle.json")
        if not path.exists():
            return {"ok": False, "reason": f"missing bundle: {path}"}
        data = _read_json(path, {})
        if not data:
            return {"ok": False, "reason": "invalid bundle json"}

        checklist = data.get("checklist", [])
        auto = [r for r in checklist if r.get("kind") == "auto"]
        auto_ok = all(r.get("passed") for r in auto if r.get("passed") is not None)
        install_ok = bool(data.get("checks", {}).get("install_proof", {}).get("ok"))
        metal = bool(data.get("metal_ready")) or (auto_ok and install_ok)

        return {
            "ok": auto_ok,
            "metal_ready": metal,
            "bundle_path": str(path),
            "auto_passed": data.get("auto_passed"),
            "auto_total": data.get("auto_total"),
            "install_proof_ok": install_ok,
            "timestamp": data.get("timestamp"),
        }


def capture_install_proof(*, target: str = "", label: str = "capture", output_dir: Optional[str] = None) -> Dict[str, Any]:
    out = Path(output_dir) if output_dir else None
    return InstallProofCollector().capture_bundle(target=target, output_dir=out, label=label)


def verify_install_proof(bundle_path: Optional[str] = None) -> Dict[str, Any]:
    path = Path(bundle_path) if bundle_path else None
    return InstallProofCollector().verify_bundle(path)
