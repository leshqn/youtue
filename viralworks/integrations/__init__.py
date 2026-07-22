"""External integration seams: trends, video gen, publishing, analytics."""

from .analytics_api import StubMetricsSource, build_metrics_source, hidden_prefs
from .publishing import build_publisher
from .trends import StubTrendSource, build_trend_source
from .video import build_video_generator

__all__ = [
    "StubMetricsSource",
    "build_metrics_source",
    "hidden_prefs",
    "build_publisher",
    "StubTrendSource",
    "build_trend_source",
    "build_video_generator",
]
