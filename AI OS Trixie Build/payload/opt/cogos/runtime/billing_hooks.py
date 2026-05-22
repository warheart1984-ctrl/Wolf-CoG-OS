"""Compute tier billing hooks — usage metering scaffold (Phase C)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root


def _config_path() -> Path:
    return cogos_root() / "config" / "billing_hooks.json"


def load_config() -> Dict[str, Any]:
    path = _config_path()
    default = {"version": "1.0", "enabled": False, "meters": {}}
    if not path.exists():
        return default
    try:
        return {**default, **json.loads(path.read_text(encoding="utf-8-sig"))}
    except Exception:
        return default


def _usage_log() -> Path:
    return cogos_root() / "memory" / "billing" / "usage.jsonl"


def maybe_meter(
    capability: str,
    profile_id: str,
    tier: str,
    allowed: bool,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    cfg = load_config()
    if not cfg.get("enabled"):
        return
    meters = cfg.get("meters", {})
    meter = meters.get(capability) or meters.get(capability.split(".")[0] + ".*")
    weight = int(meter.get("weight", 1)) if isinstance(meter, dict) else 1
    if not allowed and weight == 0:
        weight = 1
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "capability": capability,
        "profile_id": profile_id,
        "tier": tier,
        "allowed": allowed,
        "weight": weight if allowed else 0,
        "unit": meter.get("unit", "event") if isinstance(meter, dict) else "event",
    }
    if extra:
        row["extra"] = extra
    _usage_log().parent.mkdir(parents=True, exist_ok=True)
    with _usage_log().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def status() -> Dict[str, Any]:
    cfg = load_config()
    log = _usage_log()
    rows: List[Dict[str, Any]] = []
    if log.exists():
        for line in log.read_text(encoding="utf-8").strip().splitlines()[-500:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    by_tier: Dict[str, int] = {}
    by_cap: Dict[str, int] = {}
    for row in rows:
        if row.get("allowed"):
            by_tier[row.get("tier", "?")] = by_tier.get(row.get("tier", "?"), 0) + int(row.get("weight", 1))
            cap = row.get("capability", "?")
            by_cap[cap] = by_cap.get(cap, 0) + 1
    return {
        "ok": True,
        "enabled": bool(cfg.get("enabled")),
        "events_total": len(rows),
        "allowed_events": sum(1 for r in rows if r.get("allowed")),
        "weighted_units": sum(int(r.get("weight", 0)) for r in rows if r.get("allowed")),
        "by_tier": by_tier,
        "top_capabilities": dict(sorted(by_cap.items(), key=lambda x: x[1], reverse=True)[:12]),
    }


def export_usage(*, limit: int = 1000) -> Dict[str, Any]:
    log = _usage_log()
    if not log.exists():
        return {"ok": True, "events": [], "path": str(log)}
    lines = log.read_text(encoding="utf-8").strip().splitlines()[-limit:]
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except Exception:
            continue
    export_path = cogos_root() / "memory" / "billing" / "export_latest.json"
    export_path.write_text(json.dumps({"events": events, "summary": status()}, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "count": len(events), "path": str(export_path)}


def reset_usage() -> Dict[str, Any]:
    log = _usage_log()
    if log.exists():
        archive = cogos_root() / "memory" / "billing" / f"usage-archive-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        archive.write_text(log.read_text(encoding="utf-8"), encoding="utf-8")
        log.unlink()
    return {"ok": True, "reset": True}
