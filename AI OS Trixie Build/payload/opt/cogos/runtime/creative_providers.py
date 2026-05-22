"""
Creative lane providers — swap stubs for governed AAIS-style adapters.

Keeps artifact contract in creative_modules._write_artifact unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _aais_beatbox_adapter():
    """Import BeatboxAdapter from AAIS-main when present on dev host."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "AAIS-main" / "external" / "ai" / "beatbox"
        if candidate.is_dir():
            pkg_root = str(candidate.parent.parent.parent)
            if pkg_root not in sys.path:
                sys.path.insert(0, pkg_root)
            try:
                from external.ai.beatbox.adapter import BeatboxAdapter, SimpleBeatboxFallback  # type: ignore

                return BeatboxAdapter(fallback=SimpleBeatboxFallback())
            except Exception:
                pass
            try:
                sys.path.insert(0, str(candidate))
                from adapter import BeatboxAdapter, SimpleBeatboxFallback  # type: ignore

                return BeatboxAdapter(fallback=SimpleBeatboxFallback())
            except Exception:
                pass
    return None


class StoryForgeProvider:
    """Deterministic narrative provider (swap slot for full Story Forge repo)."""

    def draft_scenes(self, prompt: str, *, target: str = "game") -> List[Dict[str, Any]]:
        beats = ["opening", "rising", "complication", "payoff"]
        scenes: List[Dict[str, Any]] = []
        for idx, beat in enumerate(beats, start=1):
            scenes.append({
                "id": f"s{idx}",
                "beat": beat,
                "intent": "advance" if idx > 1 else "observe",
                "pacing": "fast" if beat == "rising" else "medium",
                "dialogue_hook": prompt[:80] if idx == 1 else "",
            })
        lower = prompt.lower()
        if "dragon" in lower:
            scenes.append({"id": "s5", "beat": "encounter", "intent": "confront", "tag": "dragon"})
        if target == "film":
            scenes = [{**s, "shot_type": "wide" if i % 2 == 0 else "close"} for i, s in enumerate(scenes)]
        return scenes


class BeatboxProvider:
    """Routes score generation through BeatboxAdapter when available."""

    def __init__(self) -> None:
        self._adapter = _aais_beatbox_adapter()

    def score(
        self,
        scene_id: str,
        *,
        mood: str = "focused",
        bpm: int = 90,
        narrative_state: str = "",
    ) -> Dict[str, Any]:
        narrative = narrative_state or f"scene {scene_id} mood {mood}"
        input_data = {
            "narrative_state": narrative,
            "emotion": mood,
            "pacing": "medium" if bpm < 100 else "fast",
            "scene_id": scene_id,
            "bpm": bpm,
        }
        if self._adapter:
            out = self._adapter.generate(input_data)
            return {
                "provider": out.get("metadata", {}).get("provider", "beatbox_adapter"),
                "status": out.get("status", "failed"),
                "audio_file": out.get("audio_file"),
                "duration": out.get("duration", 0.0),
                "scene_state": {
                    "energy": 60,
                    "tension": 40,
                    "valence": 0.6,
                    "focus": 70,
                    "mood": mood,
                    "bpm": bpm,
                },
                "adapter": True,
            }
        return {
            "provider": "cogos_stub",
            "status": "fallback",
            "audio_file": f"/opt/cogos/memory/creative/beatbox/{scene_id}-score.wav",
            "duration": 1.0,
            "scene_state": {
                "energy": 55,
                "tension": 35,
                "valence": 0.5,
                "focus": 65,
                "mood": mood,
                "bpm": bpm,
            },
            "adapter": False,
        }
