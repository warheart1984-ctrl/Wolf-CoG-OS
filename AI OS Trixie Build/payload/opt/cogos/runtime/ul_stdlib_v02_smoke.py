"""Smoke checks for UL stdlib v0.2."""

from __future__ import annotations

from ul.ul_stdlib import STDLIB_VERSION, call_stdlib, stdlib_manifest


def main() -> int:
    assert STDLIB_VERSION in ("0.2.0", "0.3.0", "0.4.0")
    manifest = stdlib_manifest()
    assert "workflow" in manifest["groups"]
    assert "workflow.suggest" in manifest["groups"]["workflow"]
    assert "storage.raid_proposals" in manifest["groups"]["storage"]

    raid = call_stdlib("storage.raid_proposals", [])
    assert "ok" in raid

    hotplug = call_stdlib("device.hotplug_summary", [])
    assert hotplug.get("ok")

    workflow = call_stdlib("workflow.suggest", [])
    assert workflow.get("ok") is not False

    print("ul_stdlib_v02_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
