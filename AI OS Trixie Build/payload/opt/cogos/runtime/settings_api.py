"""Aggregated settings snapshot for Phase B shell."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from governance_invariant_engine import cogos_root
from first_run_wizard import FirstRunWizard
from user_profiles import UserProfileManager


def settings_snapshot() -> Dict[str, Any]:
    root = cogos_root()
    mesh_path = root / "config" / "mesh.json"
    watch_path = root / "config" / "automatic_watch.json"
    release_path = root / "config" / "release_manifest.json"

    def _read(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return default

    profiles = UserProfileManager()
    return {
        "ok": True,
        "profiles": profiles.list_profiles(),
        "active_profile": profiles.active_id,
        "first_run": FirstRunWizard().status(),
        "mesh": _read(mesh_path, {}),
        "automatic_watch": _read(watch_path, {}),
        "release": _read(release_path, {}),
        "env": {
            "cogos_root": str(root),
            "desktop_port": int(__import__("os").environ.get("COGOS_DESKTOP_PORT", "8081")),
        },
    }


def update_settings(patch: Dict[str, Any], *, profile_id: str = "operator") -> Dict[str, Any]:
    root = cogos_root()
    updated: Dict[str, Any] = {"ok": True, "applied": []}

    if patch.get("active_profile"):
        UserProfileManager().set_active(str(patch["active_profile"]))
        updated["applied"].append("active_profile")

    if "mesh" in patch and isinstance(patch["mesh"], dict):
        mesh_path = root / "config" / "mesh.json"
        current = {}
        if mesh_path.exists():
            try:
                current = json.loads(mesh_path.read_text(encoding="utf-8-sig"))
            except Exception:
                pass
        current.update(patch["mesh"])
        mesh_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        updated["applied"].append("mesh")

    if "automatic_watch" in patch and isinstance(patch["automatic_watch"], dict):
        watch_path = root / "config" / "automatic_watch.json"
        current = {}
        if watch_path.exists():
            try:
                current = json.loads(watch_path.read_text(encoding="utf-8-sig"))
            except Exception:
                pass
        current.update(patch["automatic_watch"])
        watch_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        updated["applied"].append("automatic_watch")

    if patch.get("first_run_apply") and isinstance(patch["first_run_apply"], dict):
        fr = patch["first_run_apply"]
        out = FirstRunWizard().apply(
            hostname=str(fr.get("hostname", "cogos")),
            profile_id=str(fr.get("profile_id", profile_id)),
            display_name=str(fr.get("display_name", "Operator")),
            mode_default=str(fr.get("mode_default", "automatic")),
            workspace_name=str(fr.get("workspace_name", "Home Base")),
            enable_kid=bool(fr.get("enable_kid")),
        )
        updated["first_run"] = out
        updated["applied"].append("first_run_apply")

    updated["snapshot"] = settings_snapshot()
    return updated
