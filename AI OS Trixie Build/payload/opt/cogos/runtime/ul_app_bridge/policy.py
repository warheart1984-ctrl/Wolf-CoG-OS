"""LawPulse-style path and capability policy for UL App Bridge."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from governance_invariant_engine import cogos_root


def load_policy() -> Dict[str, Any]:
    path = cogos_root() / "config" / "ul_app_bridge_policy.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _expand_home(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("~/"):
        return str(Path.home() / p[2:])
    return p


def profile_for_sigil_record(record: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    profiles = policy.get("profiles") or {}
    return profiles.get(record.get("profile_id", ""), {})


def check_path(path: str, profile: Dict[str, Any], *, write: bool = False) -> Tuple[bool, str, str]:
    norm = Path(_expand_home(path)).resolve()
    norm_s = str(norm).replace("\\", "/")
    home = str(Path.home().resolve()).replace("\\", "/")
    for deny in profile.get("deny_path_prefixes") or []:
        d = Path(_expand_home(deny)).resolve()
        d_s = str(d).replace("\\", "/")
        if norm_s.startswith(d_s) or norm == d:
            rule = "deny_write_outside_home" if write else "deny_read_sensitive"
            return False, "ERR_POLICY_DENY", rule
    allowed_any = False
    prefixes = list(profile.get("allowed_path_prefixes") or [])
    prefixes.append(home)
    for allow in prefixes:
        a = _expand_home(allow).replace("\\", "/")
        if a in ("/home", "~/"):
            a = home
        a_path = Path(a).resolve() if a else norm
        a_s = str(a_path).replace("\\", "/")
        if norm_s.startswith(a_s):
            allowed_any = True
            break
    if not allowed_any:
        return False, "ERR_FS_FORBIDDEN", "path_outside_allowed_roots"
    return True, "", ""


def check_cap(cap: str, caps: List[str]) -> Tuple[bool, str]:
    if cap in caps:
        return True, ""
    return False, "ERR_TOOL_FORBIDDEN"
