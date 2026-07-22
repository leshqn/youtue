"""The single model client every agent uses for LLM calls.

Owns retries with backoff, per-call cost logging (so spend never runs unbounded),
and an easy swap of provider/model via config. Because there is exactly one
client, cost and reliability policy live in one place.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from .providers import Provider, Usage, build_provider

# Rough public price per 1M tokens (USD). Overridable; used only for the spend log.
_DEFAULT_PRICES = {
    "input_per_mtok": 3.0,
    "output_per_mtok": 15.0,
}


@dataclass
class CallLog:
    agent: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    retries: int
    ts: float = field(default_factory=time.time)


class ModelClient:
    def __init__(
        self,
        provider: str = "stub",
        model: str = "stub-model",
        api_key: str = "",
        max_retries: int = 3,
        prices: Optional[dict] = None,
    ) -> None:
        self.provider_name = provider
        self.model = model
        self._provider: Provider = build_provider(provider, model, api_key)
        self.max_retries = max_retries
        # The offline stub is free — never log phantom spend for it.
        if self._provider.name in ("stub", "none", ""):
            self.prices = {"input_per_mtok": 0.0, "output_per_mtok": 0.0}
        else:
            self.prices = prices or dict(_DEFAULT_PRICES)
        self.call_log: List[CallLog] = []

    @property
    def is_live(self) -> bool:
        return self._provider.name not in ("stub", "none", "")

    # --- cost accounting --------------------------------------------------- #
    def _cost(self, usage: Usage) -> float:
        return round(
            usage.input_tokens / 1_000_000 * self.prices["input_per_mtok"]
            + usage.output_tokens / 1_000_000 * self.prices["output_per_mtok"],
            6,
        )

    @property
    def total_cost_usd(self) -> float:
        return round(sum(c.cost_usd for c in self.call_log), 6)

    @property
    def total_calls(self) -> int:
        return len(self.call_log)

    # --- the one call path ------------------------------------------------- #
    def complete(self, agent: str, system: str, prompt: str, **kwargs) -> str:
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                text, usage = self._provider.complete(system, prompt, **kwargs)
                self.call_log.append(
                    CallLog(
                        agent=agent,
                        provider=self._provider.name,
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                        cost_usd=self._cost(usage),
                        retries=attempt,
                    )
                )
                return text
            except Exception as exc:  # noqa: BLE001 - retry any provider failure
                last_err = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt * 0.01, 0.5))  # tiny backoff
                    continue
        raise RuntimeError(f"LLM call failed after retries: {last_err}")
