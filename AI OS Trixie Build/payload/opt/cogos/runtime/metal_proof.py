"""
metal_proof.py — Full metal proof capture (checklist #4–#5 + RAID/backup/idle).

Run on live or installed Wolf CoG OS after operator confirms boot/persist/auto.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root
from install_proof import InstallProofCollector, utc_now


def _run_json(cmd: List[str], timeout: int = 600) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        text = (completed.stdout or "").strip()
        if text.startswith("{"):
            data = json.loads(text)
            if isinstance(data, dict):
                data.setdefault("returncode", completed.returncode)
                return data
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": text[:8000],
            "stderr": (completed.stderr or "").strip()[:2000],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _which(name: str) -> Optional[str]:
    for prefix in ("/usr/local/bin", "/opt/cogos/bin"):
        path = Path(prefix) / name
        if path.exists():
            return str(path)
    return None


def _run_eval_live(root: Path) -> Dict[str, Any]:
    try:
        from eval_harness import run_eval_suite

        report = run_eval_suite()
        log_path = root / "memory" / "logs" / "eval_report.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return {
            "ok": bool(report.get("ok")),
            "passed": report.get("passed"),
            "total": report.get("total"),
            "path": str(log_path),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _run_pid1_capture(root: Path) -> Dict[str, Any]:
    proof_path = root / "memory" / "logs" / "pid1_proof.json"
    cmd = _which("cogos-pid1-proof")
    if cmd:
        out = _run_json(["sh", cmd], timeout=120)
        if proof_path.exists():
            data = json.loads(proof_path.read_text(encoding="utf-8-sig"))
            return {
                "ok": bool(data.get("pid1_gate_ok")),
                "path": str(proof_path),
                "summary": data,
                "cli": out,
            }
    if proof_path.exists():
        data = json.loads(proof_path.read_text(encoding="utf-8-sig"))
        return {"ok": bool(data.get("pid1_gate_ok")), "path": str(proof_path), "summary": data}
    return {"ok": False, "reason": "pid1_proof.json missing; run cogos-pid1-proof on metal"}


def idle_soak(minutes: int = 30, interval_sec: int = 60) -> Dict[str, Any]:
    root = cogos_root()
    end = time.time() + minutes * 60
    samples: List[Dict[str, Any]] = []
    errors: List[str] = []

    while time.time() < end:
        row: Dict[str, Any] = {"ts": utc_now()}
        pid_file = Path("/run/cogos-desktop.pid")
        row["desktop_pid_file"] = pid_file.exists()
        corridor = root / "memory" / "logs" / "determinism_corridor.json"
        row["corridor_log_exists"] = corridor.exists()
        if corridor.exists():
            try:
                row["corridor_bytes"] = corridor.stat().st_size
            except OSError:
                pass
        ledger_ok = None
        try:
            from pattern_ledger import PatternLedger

            ledger_ok = PatternLedger(root=root).verify_chain().get("ok")
        except Exception as exc:
            ledger_ok = False
            errors.append(f"ledger: {exc}")
        row["ledger_ok"] = ledger_ok
        samples.append(row)
        time.sleep(interval_sec)

    ok = all(s.get("ledger_ok") is not False for s in samples) and len(samples) > 0
    return {
        "ok": ok,
        "minutes": minutes,
        "samples": len(samples),
        "interval_sec": interval_sec,
        "errors": errors,
        "timeline": samples,
    }


def capture_full_metal_proof(
    *,
    target: str = "",
    label: str = "metal",
    output_dir: Optional[Path] = None,
    run_eval: bool = True,
    idle_minutes: int = 0,
) -> Dict[str, Any]:
    root = cogos_root()
    collector = InstallProofCollector(root=root)
    out_dir = output_dir or (root / "memory" / "logs" / "metal_proof_bundles" / f"{label}-{utc_now().replace(':', '')}")
    out_dir.mkdir(parents=True, exist_ok=True)

    extras: Dict[str, Any] = {"timestamp": utc_now(), "label": label, "output_dir": str(out_dir)}

    if run_eval:
        extras["eval_live"] = _run_eval_live(root)
    extras["pid1"] = _run_pid1_capture(root)

    ds = _which("cogos-device-storage")
    if ds:
        extras["device_storage"] = _run_json(["sh", ds, "status"])
        extras["raid_scan"] = _run_json(["sh", ds, "raid-scan"])
        extras["raid_list"] = _run_json(["sh", ds, "raid-list"])
        extras["raid_status"] = _run_json(["sh", ds, "raid-status"])
    else:
        extras["device_storage"] = {"ok": None, "skipped": "cogos-device-storage not found"}

    for key, sub in (("auto", "status"), ("recovery", "verify")):
        path = _which(f"cogos-{key}" if key != "recovery" else "cogos-recovery")
        if not path:
            extras[key] = {"ok": None, "skipped": f"cogos-{key} not found"}
            continue
        extras[key] = _run_json(["sh", path, sub])

    backup = _which("cogos-backup")
    if backup:
        extras["backup_list"] = _run_json(["sh", backup, "list"])
    else:
        extras["backup_list"] = {"ok": None, "skipped": "cogos-backup not found"}

    k32 = _which("cogos-k32")
    extras["k32"] = _run_json(["sh", k32, "status"]) if k32 else {"ok": None, "skipped": "cogos-k32 not found"}

    ship_py = root / "bin" / "cogos_ship.py"
    extras["ship"] = _run_json(["python3", str(ship_py), "preflight"]) if ship_py.exists() else {"ok": None}

    if idle_minutes > 0:
        soak = idle_soak(minutes=idle_minutes)
        extras["idle_soak"] = soak
        (out_dir / "idle_soak.json").write_text(json.dumps(soak, indent=2) + "\n", encoding="utf-8")

    bundle = collector.capture_bundle(target=target, output_dir=out_dir, label=label)
    if run_eval and extras.get("eval_live"):
        bundle.setdefault("checks", {})["eval_live"] = extras["eval_live"]
    bundle.setdefault("checks", {})["pid1_live"] = extras.get("pid1", {})
    bundle["metal_extras"] = {k: v for k, v in extras.items() if k not in ("timestamp", "label", "output_dir")}
    bundle["metal_proof_ok"] = bool(
        extras.get("pid1", {}).get("ok")
        and (extras.get("eval_live", {}).get("ok") if run_eval else True)
    )

    merged_path = out_dir / "metal_proof_bundle.json"
    merged_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    extras_path = out_dir / "metal_extras.json"
    extras_path.write_text(json.dumps(extras, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    bundle["metal_extras_path"] = str(extras_path)
    bundle["merged_bundle_path"] = str(merged_path)
    return bundle
