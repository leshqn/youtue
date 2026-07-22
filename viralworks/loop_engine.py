"""The runtime loop — VIRALWORKS' core operating principle.

Every department runs this cycle on its own work *before* handing it downstream:

    1. define success criteria (concrete, task-specific)
    2. draft a genuine first attempt
    3. critique it against the criteria (specific, located weaknesses)
    4. revise to repair named weaknesses
    5. decide — stop when the critique finds nothing material, or after N passes

This is implemented once, here, and imported by every agent so the
critique/revise discipline is enforced *structurally* rather than left to
chance. It is generic over the output type ``T``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, List, TypeVar

T = TypeVar("T")


@dataclass
class Issue:
    """A specific, located weakness found during critique."""

    location: str    # where in the draft (e.g. "hook", "shot 2", "length")
    problem: str     # what is wrong
    severity: str    # "block" | "major" | "minor"

    @property
    def is_material(self) -> bool:
        return self.severity in ("block", "major")


@dataclass
class Critique:
    """The result of critiquing a draft against its success criteria."""

    issues: List[Issue] = field(default_factory=list)

    @property
    def material_issues(self) -> List[Issue]:
        return [i for i in self.issues if i.is_material]

    @property
    def passes(self) -> bool:
        """A draft passes when no *material* issues remain."""
        return len(self.material_issues) == 0

    def summary(self) -> str:
        if not self.issues:
            return "no issues"
        return "; ".join(f"[{i.severity}] {i.location}: {i.problem}" for i in self.issues)


@dataclass
class LoopPass(Generic[T]):
    index: int
    output: T
    critique: Critique


@dataclass
class LoopResult(Generic[T]):
    """Final output plus the full transcript of the loop for observability."""

    output: T
    passes: List[LoopPass[T]]
    converged: bool

    @property
    def num_passes(self) -> int:
        return len(self.passes)

    def transcript(self) -> List[dict]:
        return [
            {
                "pass": p.index,
                "critique": p.critique.summary(),
                "material_issues": len(p.critique.material_issues),
            }
            for p in self.passes
        ]


# Callable signatures the loop is parameterised over.
CriteriaFn = Callable[[Any], List[str]]
DraftFn = Callable[[Any, List[str]], T]
CritiqueFn = Callable[[T, List[str], Any], Critique]
ReviseFn = Callable[[T, Critique, List[str], Any], T]


class LoopEngine:
    """Runs the criteria -> draft -> critique -> revise -> decide cycle.

    ``max_passes`` caps iteration (default 4, per the operating principle). The
    loop stops early the moment a critique reports no material issues, which
    guards against 'critique theatre' — endless cosmetic rewrites.
    """

    def __init__(self, max_passes: int = 4) -> None:
        if max_passes < 1:
            raise ValueError("max_passes must be >= 1")
        self.max_passes = max_passes

    def run(
        self,
        task: Any,
        criteria_fn: CriteriaFn,
        draft_fn: DraftFn,
        critique_fn: CritiqueFn,
        revise_fn: ReviseFn,
    ) -> LoopResult[T]:
        criteria = criteria_fn(task)
        output = draft_fn(task, criteria)
        passes: List[LoopPass[T]] = []
        converged = False

        for i in range(1, self.max_passes + 1):
            critique = critique_fn(output, criteria, task)
            passes.append(LoopPass(index=i, output=output, critique=critique))
            if critique.passes:
                converged = True
                break
            if i == self.max_passes:
                break
            output = revise_fn(output, critique, criteria, task)

        return LoopResult(output=output, passes=passes, converged=converged)
