"""Trend data source — stub + live slot.

The stub is deterministic per (niche, day) so runs are reproducible while still
varying across niches. To go live, implement ``fetch`` against a platform trend
API or a ToS-respecting scraper and return the same shape.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

_TOPIC_BANK = {
    "generic": [
        "3 {niche} mistakes beginners make",
        "the fastest way to master {niche}",
        "nobody talks about this {niche} trick",
        "I tried {niche} for 30 days",
        "{niche} myths that cost you money",
        "do this before you try {niche}",
        "the only {niche} tip you need",
        "why your {niche} isn't working",
        "{niche} hacks the pros use",
        "stop wasting time on {niche}",
        "the {niche} routine that changed everything",
        "5 {niche} tools you're not using",
        "what {niche} experts won't tell you",
        "the {niche} glow-up nobody expects",
    ],
}
_SOUNDS = ["rising-beat-01", "trend-audio-lofi", "viral-clap-remix", "aesthetic-piano"]
_FORMATS = ["listicle", "tutorial", "storytime", "reaction", "transformation", "myth_busting"]
_HOOK_STYLES = ["text", "voiceover", "visual", "question", "stat"]


def _seed(niche: str, salt: str) -> int:
    return int(hashlib.sha256(f"{niche}|{salt}".encode()).hexdigest(), 16)


class StubTrendSource:
    """Deterministic, offline trend signals."""

    def __init__(self, salt: str = "day-0") -> None:
        self.salt = salt

    def fetch(self, niche: str, platforms: List[str]) -> List[Dict[str, Any]]:
        seed = _seed(niche, self.salt)
        topics = _TOPIC_BANK["generic"]
        signals: List[Dict[str, Any]] = []
        for i in range(len(topics)):
            topic = topics[i].replace("{niche}", niche)
            signals.append(
                {
                    "topic": topic,
                    "content_format": _FORMATS[(seed >> (i * 5)) % len(_FORMATS)],
                    "suggested_hook_style": _HOOK_STYLES[(seed >> (i * 7)) % len(_HOOK_STYLES)],
                    "trending_sound": _SOUNDS[(seed >> (i * 2)) % len(_SOUNDS)],
                    "hashtags": [
                        f"#{niche.replace(' ', '')}",
                        f"#{niche.replace(' ', '')}tips",
                        "#fyp",
                        "#viral",
                    ],
                    # A raw "heat" signal from the platform, 0..1.
                    "heat": ((seed >> (i * 11)) % 1000) / 1000.0,
                    "platforms": platforms,
                }
            )
        return signals


class LiveTrendSource:
    """Slot for a real trend API. Not implemented until keys/endpoints are set."""

    def __init__(self, api_config: str) -> None:
        self.api_config = api_config

    def fetch(self, niche: str, platforms: List[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "Wire a real trend API/scraper here (respect ToS + rate limits), "
            "returning the same shape as StubTrendSource.fetch()."
        )


def build_trend_source(config_value: str, salt: str = "day-0") -> StubTrendSource:
    # An empty config means stub. A real value would select LiveTrendSource.
    return StubTrendSource(salt=salt)
