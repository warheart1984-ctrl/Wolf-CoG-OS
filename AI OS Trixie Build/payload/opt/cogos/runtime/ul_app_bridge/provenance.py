"""Hash-chained UL App Bridge provenance — write is in the critical path."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root


class ULBridgeProvenance:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or (cogos_root() / "memory" / "ul_app_bridge" / "provenance.jsonl")
        self.head_path = self.path.with_suffix(".head")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prev = "GENESIS"
        self._load_head()

    def _load_head(self) -> None:
        if self.head_path.exists():
            try:
                self._prev = self.head_path.read_text(encoding="utf-8").strip() or "GENESIS"
            except OSError:
                self._prev = "GENESIS"

    def _hash_entry(self, row: Dict[str, Any]) -> str:
        return hashlib.sha256((self._prev + "|" + self._payload_blob(row)).encode()).hexdigest()

    def append(self, row: Dict[str, Any]) -> str:
        row = dict(row)
        row["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        chain_hash = self._hash_entry(row)
        row["chain_hash"] = chain_hash
        row["prev_hash"] = self._prev
        line = json.dumps(row, sort_keys=True) + "\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        self._prev = chain_hash
        self.head_path.write_text(chain_hash + "\n", encoding="utf-8")
        return chain_hash

    def _payload_blob(self, row: Dict[str, Any]) -> str:
        body = {k: v for k, v in row.items() if k not in ("chain_hash", "prev_hash")}
        return json.dumps(body, sort_keys=True, separators=(",", ":"))

    def verify(self, *, tail: int = 500) -> Dict[str, Any]:
        if not self.path.exists():
            return {"ok": True, "entries": 0}
        lines = [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        start = 0
        if tail > 0 and len(lines) > tail:
            start = len(lines) - tail
        prev = "GENESIS"
        if start > 0:
            prev_row = json.loads(lines[start - 1])
            prev = prev_row.get("chain_hash", "GENESIS")
        window = lines[start:]
        for idx, line in enumerate(window):
            row = json.loads(line)
            expected = hashlib.sha256((prev + "|" + self._payload_blob(row)).encode()).hexdigest()
            if row.get("prev_hash") != prev or row.get("chain_hash") != expected:
                return {"ok": False, "break_at": start + idx, "entries_checked": len(window)}
            prev = row["chain_hash"]
        return {"ok": True, "entries": len(window), "head": prev}
