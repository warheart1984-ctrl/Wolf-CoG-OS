"""UL App Bridge verb schema v1.0.0 — sigil is OS-injected, never caller-controlled."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

UL_BRIDGE_VERSION = "1.0.0"

OS_ERROR_MAP = {
    "ERR_POLICY_DENY": "EACCES",
    "ERR_INVARIANT_VIOLATION": "EPERM",
    "ERR_FS_FORBIDDEN": "EACCES",
    "ERR_FS_NOT_FOUND": "ENOENT",
    "ERR_NET_FORBIDDEN": "ECONNREFUSED",
    "ERR_PROC_FORBIDDEN": "EACCES",
    "ERR_TOOL_FORBIDDEN": "EACCES",
    "ERR_TOOL_NOT_FOUND": "ENOENT",
    "ERR_SIGIL_FORBIDDEN": "EACCES",
    "ERR_UL_VERSION_UNSUPPORTED": "EPERM",
}

VERB_FAMILIES = ("handshake", "fs", "net", "proc", "log", "tool")


def ul_response(
    *,
    ok: bool,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    policy: Optional[str] = None,
    details: Optional[str] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {"ok": ok}
    if data:
        row.update(data)
    if not ok:
        if error:
            row["error"] = error
        if policy:
            row["policy"] = policy
        if details:
            row["details"] = details
        row["mapped_os_error"] = OS_ERROR_MAP.get(error or "", "EPERM")
    return row


def normalize_verb(verb: str) -> str:
    v = (verb or "").strip().lower()
    if v.startswith("ul."):
        v = v[3:]
    return v
