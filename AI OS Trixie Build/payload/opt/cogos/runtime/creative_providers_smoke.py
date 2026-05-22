"""Phase B.3: creative provider swap smoke."""

from __future__ import annotations

import json
from pathlib import Path

from creative_modules import run_creative
from creative_providers import BeatboxProvider, StoryForgeProvider
from governance_invariant_engine import cogos_root


def main() -> int:
    sf = StoryForgeProvider()
    scenes = sf.draft_scenes("dragon quest", target="film")
    assert len(scenes) >= 4

    bb = BeatboxProvider()
    scored = bb.score("scene-1", mood="focused", bpm=92)
    assert scored.get("scene_state")

    story = run_creative("story_forge", "draft", prompt="dragon quest")
    assert story.ok and story.artifact_path
    body = json.loads(Path(story.artifact_path).read_text(encoding="utf-8"))
    assert body.get("provider") == "story_forge_provider"

    beat = run_creative("beatbox", "score", context={"scene_id": "scene-1", "mood": "calm"})
    assert beat.ok
    beat_body = json.loads(Path(beat.artifact_path).read_text(encoding="utf-8"))
    assert "provider" in beat_body

    log = cogos_root() / "memory" / "creative" / "artifact_log.jsonl"
    assert log.exists()
    print("creative_providers_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
