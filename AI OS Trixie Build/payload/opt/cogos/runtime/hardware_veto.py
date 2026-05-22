"""Hardware Veto contract.

CoGOS may observe and report safety conditions, but final safety authority
belongs to a separate physical fail-safe. This module intentionally has no
method that can override, disable, or emulate that hardware authority.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from governance_invariant_engine import cogos_root


REQUIRED_VETO_LINES = {
    "cut_power",
    "halt_execution",
    "freeze_bus",
    "lock_disk",
    "drop_network",
    "kill_process",
}


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


class HardwareVeto:
    """Report-only interface to an out-of-band hardware veto layer."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or cogos_root()
        self.config_path = self.root / "config" / "hardware_veto.json"
        self.config = _read_json(self.config_path, {})
        iface = self.config.get("software_interface", {})
        self.event_log = self.root / iface.get("event_log", "memory/hardware_veto/events.jsonl")
        self.proof_log = self.root / iface.get("proof_log", "memory/logs/hardware_veto_proof.json")
        self.attached_hint = self.root / iface.get("attached_hint", "memory/hardware_veto/ATTACHED")
        self.heartbeat_hint = self.root / iface.get("heartbeat_hint", "memory/hardware_veto/HEARTBEAT")

    def verify_contract(self) -> Dict[str, Any]:
        authority = self.config.get("authority", {})
        fail_safe = self.config.get("fail_safe", {})
        lines = set(self.config.get("physical_veto_lines", []))
        checks = [
            ("final_authority_physical", authority.get("final_authority") == "physical_hardware_veto"),
            ("software_report_only", authority.get("software_authority") == "report_only"),
            ("software_cannot_override", authority.get("software_can_override") is False),
            ("os_untrusted", authority.get("os_trusted") is False),
            ("runtime_untrusted", authority.get("runtime_trusted") is False),
            ("sigils_untrusted", authority.get("sigil_system_trusted") is False),
            ("out_of_band_required", fail_safe.get("out_of_band_required") is True),
            ("separate_power_rail", fail_safe.get("separate_power_rail") is True),
            ("separate_microcontroller", fail_safe.get("separate_microcontroller") is True),
            ("separate_bus", fail_safe.get("separate_bus") is True),
            ("separate_firmware", fail_safe.get("separate_firmware") is True),
            ("separate_clock", fail_safe.get("separate_clock") is True),
            ("no_dynamic_code", fail_safe.get("dynamic_code_allowed") is False),
            ("no_linux", fail_safe.get("linux_allowed") is False),
            ("no_python", fail_safe.get("python_allowed") is False),
            ("no_llm", fail_safe.get("llm_allowed") is False),
            ("no_vm", fail_safe.get("vm_allowed") is False),
            ("no_scheduler", fail_safe.get("scheduler_allowed") is False),
            ("all_veto_lines_declared", REQUIRED_VETO_LINES.issubset(lines)),
        ]
        missing = sorted(REQUIRED_VETO_LINES - lines)
        return {
            "ok": all(ok for _, ok in checks),
            "timestamp": _utc(),
            "doctrine": self.config.get("doctrine"),
            "checks": [{"name": name, "ok": ok} for name, ok in checks],
            "missing_veto_lines": missing,
            "config": str(self.config_path),
        }

    def status(self) -> Dict[str, Any]:
        contract = self.verify_contract()
        heartbeat = None
        if self.heartbeat_hint.exists():
            heartbeat = self.heartbeat_hint.read_text(encoding="utf-8", errors="replace").strip()[:200]
        attached = self.attached_hint.exists()
        return {
            "ok": contract["ok"],
            "attached": attached,
            "deployment_ready": bool(contract["ok"] and attached),
            "mode": self.config.get("software_interface", {}).get("mode", "report_only"),
            "authority": self.config.get("authority", {}),
            "physical_veto_lines": self.config.get("physical_veto_lines", []),
            "heartbeat": heartbeat,
            "contract": contract,
            "note": "Software reports only; physical hardware remains final authority.",
        }

    def report_event(self, event: str, severity: str = "info", evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        row = {
            "timestamp": _utc(),
            "event": event,
            "severity": severity,
            "evidence": evidence or {},
            "software_action": "reported_only",
            "hardware_authority": "physical_veto",
        }
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
        with self.event_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
        return {"ok": True, "reported": row, "event_log": str(self.event_log)}

    def write_proof(self) -> Dict[str, Any]:
        proof = self.status()
        proof["proof_type"] = "hardware_veto_contract"
        self.proof_log.parent.mkdir(parents=True, exist_ok=True)
        self.proof_log.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.report_event("hardware_veto_proof_written", "info", {"proof": str(self.proof_log), "attached": proof["attached"]})
        return proof


def hardware_veto_status() -> Dict[str, Any]:
    return HardwareVeto().status()
