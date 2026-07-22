"""Social publishing — stubs + live slots per platform.

Auto-publish is OFF by default (guardrail): stubs return a ``scheduled`` /
``queued_for_human_review`` status unless auto_publish is explicitly enabled.
"""

from __future__ import annotations

from typing import Any, Dict

from ..contracts import ReelSpec


class StubPublisher:
    """Offline publisher: records intent, never actually posts."""

    def __init__(self, platform: str) -> None:
        self.platform = platform

    def publish(
        self, spec: ReelSpec, scheduled_hour: int, auto_publish: bool
    ) -> Dict[str, Any]:
        status = "scheduled" if auto_publish else "queued_for_human_review"
        return {
            "platform": self.platform,
            "status": status,
            "scheduled_hour": scheduled_hour,
            "spec_id": spec.spec_id,
            "external_post_id": None,
        }


class LiveInstagramPublisher:
    platform = "instagram_reels"

    def __init__(self, api_config: str) -> None:
        self.api_config = api_config

    def publish(self, spec: ReelSpec, scheduled_hour: int, auto_publish: bool) -> Dict[str, Any]:
        raise NotImplementedError("Implement Instagram Graph API publish flow here.")


class LiveTikTokPublisher:
    platform = "tiktok"

    def __init__(self, api_config: str) -> None:
        self.api_config = api_config

    def publish(self, spec: ReelSpec, scheduled_hour: int, auto_publish: bool) -> Dict[str, Any]:
        raise NotImplementedError("Implement TikTok Content Posting API flow here.")


class LiveYouTubePublisher:
    platform = "youtube_shorts"

    def __init__(self, api_config: str) -> None:
        self.api_config = api_config

    def publish(self, spec: ReelSpec, scheduled_hour: int, auto_publish: bool) -> Dict[str, Any]:
        raise NotImplementedError("Implement YouTube Data API upload flow here.")


_PLATFORM_MAP = {
    "instagram_reels": ("instagram_graph_api", LiveInstagramPublisher),
    "tiktok": ("tiktok_api", LiveTikTokPublisher),
    "youtube_shorts": ("youtube_data_api", LiveYouTubePublisher),
}


def build_publisher(platform: str, integrations) -> Any:
    """Return a live publisher if its integration is configured, else a stub."""
    entry = _PLATFORM_MAP.get(platform)
    if entry:
        attr, live_cls = entry
        config_value = getattr(integrations, attr, "")
        if config_value:
            return live_cls(config_value)
    return StubPublisher(platform)
