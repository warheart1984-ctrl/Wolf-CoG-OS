"""Third-party and curated UL package manager (Phase C)."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from compute_tiers import ComputeTierEngine
from governance_invariant_engine import cogos_root


def _catalog_path() -> Path:
    return cogos_root() / "config" / "ul_package_catalog.json"


def load_catalog() -> Dict[str, Any]:
    path = _catalog_path()
    if not path.exists():
        return {"version": "1.0", "packages": []}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _installed_path() -> Path:
    return cogos_root() / "memory" / "packages" / "ul_installed.json"


def _installed_index() -> Dict[str, Any]:
    path = _installed_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_installed(index: Dict[str, Any]) -> None:
    path = _installed_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def _log(action: str, detail: Dict[str, Any]) -> None:
    log = cogos_root() / "memory" / "traces" / "ul_package_history.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "action": action, **detail}
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def list_ul_packages() -> List[Dict[str, Any]]:
    installed = _installed_index()
    out = []
    for pkg in load_catalog().get("packages", []):
        pid = pkg["id"]
        out.append({**pkg, "installed": pid in installed, "install_record": installed.get(pid)})
    return out


def verify_catalog() -> Dict[str, Any]:
    root = cogos_root()
    catalog = load_catalog()
    checks = []
    ok = True
    for pkg in catalog.get("packages", []):
        src = root / pkg.get("source_dir", "")
        missing = [f for f in pkg.get("ul_files", []) if not (src / f).exists()]
        row = {
            "id": pkg["id"],
            "ok": not missing,
            "source_dir": str(src),
            "missing_files": missing,
        }
        if missing:
            ok = False
        checks.append(row)
    return {"ok": ok, "packages": len(checks), "checks": checks}


def install_ul_package(package_id: str, *, profile_id: str = "operator") -> Dict[str, Any]:
    tiers = ComputeTierEngine()
    check = tiers.check("ul.pkg.install", profile_id=profile_id)
    if not check.allowed:
        check = tiers.check("pkg.install", profile_id=profile_id)
    if not check.allowed:
        tiers.log_denial(check, context={"package": package_id, "kind": "ul"})
        return {"ok": False, "error": check.reason, "tier": check.tier}

    pkg = next((p for p in load_catalog().get("packages", []) if p["id"] == package_id), None)
    if not pkg:
        return {"ok": False, "error": f"unknown ul package: {package_id}"}

    req = pkg.get("required_tier", "standard")
    tier = tiers.resolve_tier(profile_id)
    order = ["base", "standard", "elevated", "developer"]
    if req in order and tier in order and order.index(tier) < order.index(req):
        return {"ok": False, "error": f"tier {tier} insufficient (requires {req})"}

    root = cogos_root()
    src = root / pkg.get("source_dir", "")
    if not src.is_dir():
        return {"ok": False, "error": f"source missing: {src}"}

    dest = root / "memory" / "packages" / "ul" / package_id.replace(".", "_")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    record = {
        "package_id": package_id,
        "version": pkg.get("version"),
        "publisher": pkg.get("publisher"),
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "path": str(dest),
        "ul_files": pkg.get("ul_files", []),
    }
    idx = _installed_index()
    idx[package_id] = record
    _save_installed(idx)
    _log("install", record)
    return {"ok": True, "package": package_id, "record": record}


def remove_ul_package(package_id: str, *, profile_id: str = "operator") -> Dict[str, Any]:
    tiers = ComputeTierEngine()
    check = tiers.check("pkg.remove", profile_id=profile_id)
    if not check.allowed:
        return {"ok": False, "error": check.reason}

    idx = _installed_index()
    if package_id not in idx:
        return {"ok": False, "error": "not installed"}

    dest = cogos_root() / "memory" / "packages" / "ul" / package_id.replace(".", "_")
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    del idx[package_id]
    _save_installed(idx)
    _log("remove", {"package_id": package_id})
    return {"ok": True, "package_id": package_id}
