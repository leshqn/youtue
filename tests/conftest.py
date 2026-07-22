"""Shared test helpers: build an AgentContext wired to stubs + in-memory store."""

from __future__ import annotations

import pytest

from viralworks.agents.base import AgentContext
from viralworks.config import Config
from viralworks.integrations import (
    build_metrics_source,
    build_publisher,
    build_trend_source,
    build_video_generator,
)
from viralworks.learning.store import InMemoryLearningStore
from viralworks.llm.client import ModelClient


def make_ctx(niche: str = "AI tools", cycle: int = 1, store=None) -> AgentContext:
    config = Config(niche=niche)
    store = store or InMemoryLearningStore()
    publishers = {p: build_publisher(p, config.integrations) for p in config.platforms}
    return AgentContext(
        config=config,
        model=ModelClient(provider="stub"),
        store=store,
        cycle=cycle,
        trend_source=build_trend_source("", salt=f"cycle-{cycle}"),
        video_generator=build_video_generator("stub", ""),
        metrics_source=build_metrics_source(config.integrations),
        publishers=publishers,
    )


@pytest.fixture
def ctx():
    return make_ctx()
