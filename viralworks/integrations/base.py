"""Integration interfaces (seams, not lock-in).

Each external dependency is defined as a Protocol with a working stub so the whole
system runs offline, and a documented slot to drop the real implementation in.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol

from ..contracts import CreativeBrief, Metrics, PublishResult, ReelSpec


class TrendSource(Protocol):
    def fetch(self, niche: str, platforms: List[str]) -> List[Dict[str, Any]]:
        """Return raw trend signals (topics, sounds, formats, hashtags)."""
        ...


class VideoGenerator(Protocol):
    def render(self, spec: ReelSpec) -> Dict[str, Any]:
        """Return {job_id, url, cost_usd, status}. Stub returns a spec-only result."""
        ...


class Publisher(Protocol):
    platform: str

    def publish(
        self, spec: ReelSpec, scheduled_hour: int, auto_publish: bool
    ) -> Dict[str, Any]:
        ...


class MetricsSource(Protocol):
    def metrics_for(self, spec: ReelSpec, features: Dict[str, Any]) -> Metrics:
        """Return realized performance metrics for a published piece."""
        ...
