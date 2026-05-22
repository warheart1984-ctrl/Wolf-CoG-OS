"""Smoke checks for Automatic mode v2."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from automatic_mode import AutomaticModeEngine
from governance_invariant_engine import cogos_root


def main() -> int:
    root = cogos_root()
    cfg_path = root / "config" / "automatic_watch.json"
    assert cfg_path.exists()

    engine = AutomaticModeEngine(root)
    original_cfg = cfg_path.read_text(encoding="utf-8-sig")
    try:
        with tempfile.TemporaryDirectory() as td:
            watch = Path(td) / "inbox-watch"
            watch.mkdir()
            (watch / "a.txt").write_text("a", encoding="utf-8")
            cfg = json.loads(original_cfg)
            cfg["watch_folders"] = [str(watch)]
            cfg["max_daily_suggestions"] = 2
            cfg["workflow_promote_after_repeats"] = 2
            cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

            scan1 = engine.scan_watches()
            assert scan1["ok"]
            scan2 = engine.scan_watches()
            assert scan2["ok"]

            daily = engine.daily_suggestions()
            assert daily["ok"] and len(daily["suggestions"]) <= 2

            suggestions = engine.suggest_workflows()["suggestions"]
            if suggestions:
                sid = suggestions[0]["id"]
                promoted = engine.promote_workflow(sid)
                assert promoted["ok"], promoted
                assert engine.list_workflows()["workflows"]
    finally:
        cfg_path.write_text(original_cfg, encoding="utf-8")

    print("automatic_mode_v2_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
