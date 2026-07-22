"""Department 9 — Strategy ("The Boardroom").

Weekly: reads the Numbers + HR reports, sets the next objective (which niches,
which formats, what to double down on, what to kill) and updates company OKRs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..loop_engine import Critique, Issue
from .base import Agent


@dataclass
class StrategyReport:
    cycle: int
    objective: str = ""
    okrs: List[str] = field(default_factory=list)
    double_down: List[str] = field(default_factory=list)
    kill: List[str] = field(default_factory=list)


class StrategyAgent(Agent):
    name = "Boardroom"
    role = "set the next objective and OKRs from performance evidence"
    kpis = ["objective clarity", "OKR measurability", "hit rate of bets"]
    failure_modes = ["vague objectives", "unmeasurable OKRs", "no kill decisions"]

    def _criteria(self, task: Dict[str, Any]) -> List[str]:
        return [
            "a single, concrete objective for next cycle",
            "measurable OKRs (numbers, not vibes)",
            "explicit double-down and kill decisions tied to the data",
        ]

    def _draft(self, task: Dict[str, Any], criteria: List[str]) -> StrategyReport:
        return StrategyReport(cycle=int(task.get("cycle", 0)))

    def _critique(self, report: StrategyReport, criteria: List[str], task: Dict[str, Any]) -> Critique:
        issues: List[Issue] = []
        if not report.objective:
            issues.append(Issue("objective", "no objective set", "major"))
        if not report.okrs:
            issues.append(Issue("okrs", "no measurable OKRs", "major"))
        if not (report.double_down or report.kill):
            issues.append(Issue("decisions", "no double-down/kill decisions", "major"))
        return Critique(issues=issues)

    def _revise(
        self, report: StrategyReport, critique: Critique, criteria: List[str], task: Dict[str, Any]
    ) -> StrategyReport:
        analytics = task.get("analytics")
        niche = task.get("niche", "the niche")
        avg_traction = getattr(analytics, "avg_traction", 0.0)
        roi_by_format = getattr(analytics, "roi_by_format", {}) or {}
        traction_by_hook = getattr(analytics, "traction_by_hook", {}) or {}

        locations = {i.location for i in critique.issues}
        if "objective" in locations:
            best_hook = (
                max(traction_by_hook, key=lambda k: traction_by_hook[k])
                if traction_by_hook
                else "the winning hook style"
            )
            report.objective = (
                f"Double down on {niche} with {best_hook} hooks; lift avg traction "
                f"from {avg_traction:.2f} toward {min(1.0, avg_traction + 0.1):.2f} next cycle."
            )
        if "okrs" in locations:
            report.okrs = [
                f"Avg traction >= {min(1.0, avg_traction + 0.08):.2f}",
                "Blended ROI up 15% vs. this cycle",
                f"Hit {task.get('target', 10)} reels/week at flat cost per reel",
            ]
        if "decisions" in locations:
            if roi_by_format:
                best_fmt = max(roi_by_format, key=lambda k: roi_by_format[k])
                worst_fmt = min(roi_by_format, key=lambda k: roi_by_format[k])
                report.double_down = [f"Format '{best_fmt}' (highest ROI)"]
                if worst_fmt != best_fmt:
                    report.kill = [f"Format '{worst_fmt}' (lowest ROI)"]
            else:
                report.double_down = [f"{niche} core formats"]
                report.kill = ["Any format below break-even ROI"]
        return report
