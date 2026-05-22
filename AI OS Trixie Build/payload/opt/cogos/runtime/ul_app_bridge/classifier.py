"""Foreign binary classifier — static magic + exec admission hook."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def classify_binary(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"foreign": False, "reason": "not_a_file"}
    head = p.read_bytes()[:8]
    if head[:2] == b"MZ":
        return {
            "foreign": True,
            "ecosystem": "windows",
            "profile_id": "win.default.safe",
            "backend": "wine",
        }
    if head[:4] == b"\x7fELF":
        return {
            "foreign": False,
            "ecosystem": "linux",
            "profile_id": "profile.linux.foreign",
            "backend": "linux-native",
            "note": "ELF may use linux-shim for governed sensitive ops",
        }
    if head[:4] in (b"\xfe\xed\xfa", b"\xce\xfa\xed", b"\xcf\xfa\xed"):
        return {
            "foreign": True,
            "ecosystem": "macos",
            "profile_id": "profile.mac.default",
            "backend": "darling",
        }
    return {"foreign": True, "ecosystem": "unknown", "profile_id": "profile.linux.foreign", "backend": "linux-shim"}
