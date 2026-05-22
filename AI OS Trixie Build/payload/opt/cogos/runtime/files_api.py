"""Governed file browser API for Phase B shell."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root


def _allowed_roots() -> List[Path]:
    root = cogos_root()
    roots = [
        root,
        root / "memory",
        root / "memory" / "workspaces",
        Path.home(),
        Path.home() / "Downloads",
        Path.home() / "Documents",
    ]
    cfg = root / "config" / "automatic_watch.json"
    if cfg.exists():
        try:
            import json

            data = json.loads(cfg.read_text(encoding="utf-8-sig"))
            for raw in data.get("watch_folders", []):
                roots.append(Path(str(raw)).expanduser())
        except Exception:
            pass
    seen: List[Path] = []
    for p in roots:
        try:
            resolved = p.resolve()
        except OSError:
            continue
        if resolved not in seen:
            seen.append(resolved)
    return seen


def resolve_safe_path(raw: str) -> Optional[Path]:
    if not raw or raw in (".", ""):
        candidate = cogos_root()
    else:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (cogos_root() / candidate).resolve()
        else:
            candidate = candidate.resolve()
    for root in _allowed_roots():
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    return None


def list_directory(path: str = "") -> Dict[str, Any]:
    resolved = resolve_safe_path(path)
    if not resolved:
        return {"ok": False, "error": "path not allowed", "path": path}
    if not resolved.exists():
        return {"ok": False, "error": "not found", "path": str(resolved)}
    if resolved.is_file():
        return {
            "ok": True,
            "path": str(resolved),
            "kind": "file",
            "name": resolved.name,
            "size_bytes": resolved.stat().st_size,
        }
    entries: List[Dict[str, Any]] = []
    try:
        for child in sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:500]:
            try:
                st = child.stat()
                entries.append({
                    "name": child.name,
                    "path": str(child),
                    "kind": "dir" if child.is_dir() else "file",
                    "size_bytes": st.st_size if child.is_file() else 0,
                })
            except OSError:
                continue
    except PermissionError as exc:
        return {"ok": False, "error": str(exc), "path": str(resolved)}
    parent = str(resolved.parent) if resolved.parent != resolved else ""
    return {
        "ok": True,
        "path": str(resolved),
        "parent": parent,
        "roots": [str(r) for r in _allowed_roots()[:8]],
        "entries": entries,
    }
