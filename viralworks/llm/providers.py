"""LLM provider adapters.

A provider implements ``complete(system, prompt) -> (text, usage)``. The default
``StubProvider`` is deterministic and key-free so the whole company runs offline;
``AnthropicProvider`` is a documented, ready-to-fill slot for going live.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, Tuple


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int


class Provider(Protocol):
    name: str

    def complete(self, system: str, prompt: str, **kwargs) -> Tuple[str, Usage]:
        ...


def _approx_tokens(text: str) -> int:
    # ~4 chars/token is a good enough approximation for cost logging.
    return max(1, len(text) // 4)


class StubProvider:
    """Deterministic, offline provider.

    It does not fabricate a language model; it returns a stable, structured
    echo that agents use only for their free-text flourishes. All the content
    logic that actually matters (hooks, structure, heuristics) lives in the
    agents and is driven by the learning store, so the system's *behaviour* is
    real even though the prose here is templated.
    """

    name = "stub"

    def complete(self, system: str, prompt: str, **kwargs) -> Tuple[str, Usage]:
        digest = hashlib.sha256((system + "\x00" + prompt).encode()).hexdigest()[:8]
        text = f"[stub:{digest}] {prompt.strip().splitlines()[0][:120]}"
        usage = Usage(_approx_tokens(system + prompt), _approx_tokens(text))
        return text, usage


class AnthropicProvider:
    """Live provider slot for the Anthropic Messages API.

    To go live: set ``llm.provider: anthropic`` and ``llm.model`` in config.yaml,
    put ``LLM_API_KEY`` in .env, and ``pip install anthropic``. The call below is
    intentionally lazy-imported so the package has zero hard dependencies.
    """

    def __init__(self, model: str, api_key: str) -> None:
        self.name = "anthropic"
        self.model = model
        self.api_key = api_key

    def complete(self, system: str, prompt: str, **kwargs) -> Tuple[str, Usage]:
        from anthropic import Anthropic  # lazy import; only needed when live

        client = Anthropic(api_key=self.api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 1024),
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        usage = Usage(resp.usage.input_tokens, resp.usage.output_tokens)
        return text, usage


def build_provider(provider: str, model: str, api_key: str) -> Provider:
    provider = (provider or "stub").lower()
    if provider in ("stub", "", "none"):
        return StubProvider()
    if provider == "anthropic":
        if not api_key:
            # No key -> fail safe to the stub so the pipeline still runs.
            return StubProvider()
        return AnthropicProvider(model=model, api_key=api_key)
    # Unknown provider -> stub (documented behaviour, never crashes a run).
    return StubProvider()
