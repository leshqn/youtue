"""Department 7 — Scalability & Operations ("Ops").

Owns throughput and cost: batching, rate-limit handling, queueing, parallelism,
retry/backoff, and the plan to go from N reels/week to 10N without linear cost or
quality loss. Reports the bottleneck each cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..loop_engine import Critique, Issue
from .base import Agent


@dataclass
class OpsReport:
    cycle: int
    reels_produced: int
    target: int
    cost_per_reel: float
    total_cost_usd: float
    model_calls: int
    bottleneck: str = ""
    scale_plan: List[str] = field(default_factory=list)
    headroom_to_10x: str = ""


class OpsAgent(Agent):
    name = "Ops"
    role = "own throughput and cost; find the bottleneck and the plan to 10x"
    kpis = ["cost per reel", "throughput vs target", "bottleneck resolution"]
    failure_modes = ["unbounded cost", "linear cost scaling", "ignoring rate limits"]

    def _criteria(self, task: Dict[str, Any]) -> List[str]:
        return [
            "report cost per reel and throughput vs target",
            "identify the single current bottleneck",
            "give a concrete plan to reach 10x without linear cost",
        ]

    def _draft(self, task: Dict[str, Any], criteria: List[str]) -> OpsReport:
        reels = int(task.get("reels_produced", 0))
        cost = float(task.get("total_cost_usd", 0.0))
        return OpsReport(
            cycle=int(task.get("cycle", 0)),
            reels_produced=reels,
            target=int(task.get("target", 10)),
            cost_per_reel=round(cost / reels, 4) if reels else 0.0,
            total_cost_usd=round(cost, 4),
            model_calls=int(task.get("model_calls", 0)),
        )

    def _critique(self, report: OpsReport, criteria: List[str], task: Dict[str, Any]) -> Critique:
        issues: List[Issue] = []
        if not report.bottleneck:
            issues.append(Issue("bottleneck", "current bottleneck not identified", "major"))
        if not report.scale_plan:
            issues.append(Issue("scale_plan", "no plan to reach 10x", "major"))
        return Critique(issues=issues)

    def _revise(
        self, report: OpsReport, critique: Critique, criteria: List[str], task: Dict[str, Any]
    ) -> OpsReport:
        locations = {i.location for i in critique.issues}
        if "bottleneck" in locations:
            if report.reels_produced < report.target:
                report.bottleneck = (
                    "Serial pipeline throughput — pieces run one at a time; "
                    "Creative/QA loops dominate wall-clock."
                )
            else:
                report.bottleneck = "Video render cost per reel once a live provider is wired."
        if "scale_plan" in locations:
            report.scale_plan = [
                "Batch Discovery once per cycle; fan out pieces to a worker pool.",
                "Parallelise per-piece pipelines (Creative/Production/QA are independent).",
                "Cache trend fetches and LLM system prompts to cut redundant spend.",
                "Add rate-limit-aware queue with exponential backoff per integration.",
                "Cap per-cycle spend via a budget guard in the ModelClient.",
            ]
            report.headroom_to_10x = (
                "10x reachable with a worker pool + batching; cost stays sublinear "
                "via prompt caching and shared trend fetches."
            )
        return report
