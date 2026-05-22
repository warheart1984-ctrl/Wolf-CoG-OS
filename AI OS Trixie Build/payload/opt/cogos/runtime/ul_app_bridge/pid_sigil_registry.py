"""Trusted PID → sigil map. Sigil is assigned at exec admission, never from verb args."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root


@dataclass
class SigilRecord:
    pid: int
    sigil: str
    profile_id: str
    bridge_class: str
    backend: str
    caps: List[str]
    parent_sigil: Optional[str] = None
    spawn_mode: str = "inherit"
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "sigil": self.sigil,
            "profile_id": self.profile_id,
            "bridge_class": self.bridge_class,
            "backend": self.backend,
            "caps": self.caps,
            "parent_sigil": self.parent_sigil,
            "spawn_mode": self.spawn_mode,
            "created_at": self.created_at,
        }


class PidSigilRegistry:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or (cogos_root() / "memory" / "ul_app_bridge" / "pid_sigil_map.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rows: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8-sig"))
                self._rows = {str(k): v for k, v in (data.get("pids") or {}).items()}
            except Exception:
                self._rows = {}

    def _save(self) -> None:
        self.path.write_text(
            json.dumps({"version": "1.0", "pids": self._rows}, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def derive_sigil(binary_hint: str, profile_id: str) -> str:
        blob = f"{profile_id}:{binary_hint}:{time.time_ns()}"
        return "sigil-" + hashlib.sha256(blob.encode()).hexdigest()[:16]

    @staticmethod
    def derive_child_sigil(parent: SigilRecord, requested_caps: List[str]) -> str:
        allowed = set(parent.caps) & set(requested_caps)
        cap_key = ",".join(sorted(allowed))
        blob = f"{parent.sigil}:delegated:{cap_key}"
        return "sigil-" + hashlib.sha256(blob.encode()).hexdigest()[:16]

    def register(
        self,
        pid: int,
        *,
        profile_id: str,
        bridge_class: str,
        backend: str,
        caps: List[str],
        sigil: Optional[str] = None,
        parent_sigil: Optional[str] = None,
        spawn_mode: str = "inherit",
        binary_hint: str = "foreign",
    ) -> SigilRecord:
        record = SigilRecord(
            pid=pid,
            sigil=sigil or self.derive_sigil(binary_hint, profile_id),
            profile_id=profile_id,
            bridge_class=bridge_class,
            backend=backend,
            caps=list(caps),
            parent_sigil=parent_sigil,
            spawn_mode=spawn_mode,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._rows[str(pid)] = record.to_dict()
        self._save()
        return record

    def lookup(self, pid: Optional[int] = None) -> Optional[SigilRecord]:
        pid = pid if pid is not None else os.getpid()
        row = self._rows.get(str(pid))
        if not row:
            return None
        return SigilRecord(**row)

    def unregister(self, pid: int) -> None:
        self._rows.pop(str(pid), None)
        self._save()
