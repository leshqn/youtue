"""Department 8 — HR ("People Ops for Agents").

Manages the agent roster itself: evaluates each agent against its KPIs, tunes
underperformers, spins up new specialists when a gap appears (e.g. a dedicated
Hook Writer for a hot niche), and retires agents that don't earn their keep. HR
is how the company grows itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Any, Dict, List

from ..contracts import PieceRecord
from ..loop_engine import Critique, Issue
from .base import Agent


@dataclass
class HRReport:
    cycle: int
    scorecards: Dict[str, float] = field(default_factory=dict)
    tune: List[str] = field(default_factory=list)
    spawn: List[str] = field(default_factory=list)
    retire: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)


def _correlation(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return round(num / (dx * dy), 3)


class HRAgent(Agent):
    name = "People Ops"
    role = "evaluate, tune, spawn and retire agents to grow the company"
    kpis = ["roster ROI", "specialist hit rate", "calibration improvement"]
    failure_modes = ["keeping dead weight", "premature retirement", "over-hiring"]

    def _criteria(self, task: Dict[str, Any]) -> List[str]:
        return [
            "score every agent against a KPI proxy from real outcomes",
            "take at least one concrete action (tune / spawn / retire) when warranted",
            "justify actions with evidence, not vibes",
        ]

    def _draft(self, task: Dict[str, Any], criteria: List[str]) -> HRReport:
        pieces: List[PieceRecord] = task.get("pieces", [])
        report = HRReport(cycle=int(task.get("cycle", 0)))
        # Data-driven scorecards.
        if pieces:
            calib = _correlation(
                [p.predicted_traction for p in pieces],
                [p.traction_score for p in pieces],
            )
            report.scorecards["R&D"] = round((calib + 1) / 2, 3)  # -1..1 -> 0..1
            report.scorecards["Studio"] = round(mean(p.traction_score for p in pieces), 3)
            report.scorecards["The Numbers"] = 1.0  # reporting completeness enforced by its loop
        return report

    def _critique(self, report: HRReport, criteria: List[str], task: Dict[str, Any]) -> Critique:
        issues: List[Issue] = []
        if not report.scorecards and task.get("pieces"):
            issues.append(Issue("scorecards", "no agent scored", "major"))
        if not (report.tune or report.spawn or report.retire) and task.get("pieces"):
            issues.append(Issue("actions", "scored but took no roster action", "major"))
        return Critique(issues=issues)

    def _revise(
        self, report: HRReport, critique: Critique, criteria: List[str], task: Dict[str, Any]
    ) -> HRReport:
        pieces: List[PieceRecord] = task.get("pieces", [])
        locations = {i.location for i in critique.issues}
        if "scorecards" in locations and pieces:
            report.scorecards["R&D"] = round(
                (_correlation(
                    [p.predicted_traction for p in pieces],
                    [p.traction_score for p in pieces],
                ) + 1) / 2,
                3,
            )
            report.scorecards["Studio"] = round(mean(p.traction_score for p in pieces), 3)
        if "actions" in locations and pieces:
            # Tune Discovery if its calibration is weak.
            if report.scorecards.get("R&D", 1.0) < 0.6:
                report.tune.append(
                    "R&D: recalibrate predicted_traction scoring — predictions poorly "
                    "track realized traction."
                )
            # Spawn a Hook Specialist when hook style clearly separates winners.
            by_hook: Dict[str, List[float]] = {}
            for p in pieces:
                by_hook.setdefault(p.hook_style, []).append(p.traction_score)
            if len(by_hook) >= 2:
                spread = max(mean(v) for v in by_hook.values()) - min(
                    mean(v) for v in by_hook.values()
                )
                if spread > 0.15:
                    best = max(by_hook, key=lambda k: mean(by_hook[k]))
                    report.spawn.append(
                        f"Hook Specialist ({best} hooks) for '{pieces[0].niche}' — "
                        f"hook style separates traction by {spread:.2f}."
                    )
            # Retire chronically weak formats from rotation.
            by_fmt: Dict[str, List[float]] = {}
            for p in pieces:
                by_fmt.setdefault(p.content_format, []).append(p.traction_score)
            if len(by_fmt) >= 2:
                worst = min(by_fmt, key=lambda k: mean(by_fmt[k]))
                if mean(by_fmt[worst]) < 0.35:
                    report.retire.append(
                        f"Format '{worst}' underperforms (traction "
                        f"{mean(by_fmt[worst]):.2f}) — drop from rotation."
                    )
            report.changes = report.tune + report.spawn + report.retire
            if not report.changes:
                report.changes = ["Roster healthy — no changes this cycle."]
        return report
