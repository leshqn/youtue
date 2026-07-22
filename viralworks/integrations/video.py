"""Video generation — stub + live slot.

Until a provider is wired, Production ships a complete render-ready spec and the
stub returns a spec-only result (no URL). Flip in a real text-to-video provider
by implementing ``render``.
"""

from __future__ import annotations

from typing import Any, Dict

from ..contracts import ReelSpec


class StubVideoGenerator:
    """Returns a spec-only result: no render, small notional cost."""

    name = "stub"

    def render(self, spec: ReelSpec) -> Dict[str, Any]:
        return {
            "job_id": None,
            "url": None,
            "status": "spec_only",
            "cost_usd": 0.0,
            "note": "No video provider wired — shipping render-ready spec + storyboard.",
        }


class LiveVideoGenerator:
    """Slot for a real text-to-video API (e.g. a Sora/Runway/Kling-style provider)."""

    def __init__(self, provider: str, api_key: str) -> None:
        self.name = provider
        self.api_key = api_key

    def render(self, spec: ReelSpec) -> Dict[str, Any]:
        raise NotImplementedError(
            "Call your text-to-video provider with spec.render_prompts + timings, "
            "return {job_id, url, status, cost_usd}."
        )


def build_video_generator(provider: str, api_key: str):
    provider = (provider or "stub").lower()
    if provider in ("stub", "", "none") or not api_key:
        return StubVideoGenerator()
    return LiveVideoGenerator(provider=provider, api_key=api_key)
