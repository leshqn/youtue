"""The common Agent interface every department implements.

An Agent has a name, role, system prompt, KPIs, known failure modes, and a
``run(task) -> LoopResult`` that is *always* wrapped by the shared LoopEngine.
Subclasses implement the four loop hooks (`_criteria`, `_draft`, `_critique`,
`_revise`); the base guarantees the critique/revise discipline runs structurally.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List

from ..llm.client import ModelClient
from ..loop_engine import Critique, LoopEngine, LoopResult

if TYPE_CHECKING:  # avoid an import cycle: learning -> growth -> agents -> base
    from ..config import Config
    from ..learning.store import LearningStore


@dataclass
class AgentContext:
    """Shared company context handed to every agent."""

    config: Config
    model: ModelClient
    store: LearningStore
    cycle: int
    # Integrations (built by the Orchestrator; agents that don't need them ignore).
    trend_source: Any = None
    video_generator: Any = None
    metrics_source: Any = None
    publishers: dict = field(default_factory=dict)

    def heuristics(self, niche: str) -> dict:
        """Active, learned playbook heuristics for a niche (or cold-start defaults)."""
        return self.store.playbook_heuristics(niche)


class Agent(ABC):
    #: short human name, e.g. "R&D"
    name: str = "Agent"
    #: one-line role
    role: str = "generic agent"
    #: measurable KPIs this agent is evaluated on by HR
    kpis: List[str] = []
    #: known failure modes the critique step must actively check for
    failure_modes: List[str] = []

    def __init__(self, ctx: AgentContext, max_passes: int = 4) -> None:
        self.ctx = ctx
        self.loop = LoopEngine(max_passes=max_passes)

    # --- identity ---------------------------------------------------------- #
    @property
    def system_prompt(self) -> str:
        cfg = self.ctx.config
        return (
            f"You are the {self.name} department of {cfg.company_name}, "
            f"an autonomous short-form video studio. Role: {self.role}. "
            f"Brand voice: {cfg.brand_voice}. North star: {cfg.primary_goal}. "
            f"Always run a criteria->draft->critique->revise loop before shipping. "
            f"Actively guard against your known failure modes: "
            f"{', '.join(self.failure_modes) or 'none recorded'}."
        )

    # --- the four loop hooks (subclasses implement) ------------------------ #
    @abstractmethod
    def _criteria(self, task: Any) -> List[str]: ...

    @abstractmethod
    def _draft(self, task: Any, criteria: List[str]) -> Any: ...

    @abstractmethod
    def _critique(self, output: Any, criteria: List[str], task: Any) -> Critique: ...

    @abstractmethod
    def _revise(
        self, output: Any, critique: Critique, criteria: List[str], task: Any
    ) -> Any: ...

    # --- the one entrypoint ------------------------------------------------ #
    def run(self, task: Any) -> LoopResult:
        """Execute the runtime loop and return the final output + transcript."""
        return self.loop.run(
            task, self._criteria, self._draft, self._critique, self._revise
        )

    # --- convenience for subclasses --------------------------------------- #
    def _llm(self, prompt: str, **kwargs) -> str:
        return self.ctx.model.complete(self.name, self.system_prompt, prompt, **kwargs)

    def _maybe_llm(self, prompt: str, fallback: str, **kwargs) -> str:
        """Call the model (always, so the seam + cost log are exercised), but only
        use its output when a *live* provider is wired. Offline, the deterministic
        template ``fallback`` is authoritative — the stub never writes content.
        """
        try:
            text = self._llm(prompt, **kwargs)
        except Exception:
            return fallback
        return text if self.ctx.model.is_live else fallback
