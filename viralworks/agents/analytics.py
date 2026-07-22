"""Department 6 — ROI, Finance & Analytics ("The Numbers").

The scoreboard. Pulls per-post performance, ties it to cost per reel, computes
ROI per piece and per format/niche, and flags winners and losers. Feeds hard
evidence to the Self-Growth Engine. No vanity metrics — the loop actively
rejects a report that leans on raw views alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..contracts import Metrics, PieceRecord, ReelSpec
from ..loop_engine import Critique, Issue
from .base import Agent


@dataclass
class AnalyticsReport:
    cycle: int
    total_views: int = 0
    total_cost_usd: float = 0.0
    avg_traction: float = 0.0
    blended_roi: float = 0.0
    leaderboard: List[Dict[str, Any]] = field(default_factory=list)
    roi_by_format: Dict[str, float] = field(default_factory=dict)
    traction_by_hook: Dict[str, float] = field(default_factory=dict)
    winners: List[str] = field(default_factory=list)
    losers: List[str] = field(default_factory=list)


def _avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


class AnalyticsAgent(Agent):
    name = "The Numbers"
    role = "measure real performance, compute ROI, and flag winners and losers"
    kpis = ["ROI accuracy", "winner/loser precision", "north-star coverage"]
    failure_modes = ["vanity metrics", "ignoring cost", "no per-format breakdown"]

    # --- per-piece measurement (not a loop; a direct pull) ----------------- #
    def measure(self, spec: ReelSpec, features: Dict[str, Any]) -> Metrics:
        return self.ctx.metrics_source.metrics_for(spec, features)

    # --- cycle-level report (runs the loop) -------------------------------- #
    def _criteria(self, task: List[PieceRecord]) -> List[str]:
        return [
            "report the north-star metrics (traction, follows, ROI), not just views",
            "break ROI down by format and traction by hook style",
            "name concrete winners and losers with evidence",
            "tie performance to cost (ROI), never views alone",
        ]

    def _draft(self, task: List[PieceRecord], criteria: List[str]) -> AnalyticsReport:
        cycle = task[0].cycle if task else 0
        report = AnalyticsReport(cycle=cycle)
        # Deliberately thin first pass: raw reach + leaderboard only.
        report.total_views = sum(p.views for p in task)
        report.total_cost_usd = round(sum(p.cost_usd for p in task), 4)
        report.leaderboard = [
            {"piece_id": p.piece_id, "topic": p.topic, "views": p.views}
            for p in sorted(task, key=lambda p: p.views, reverse=True)[:5]
        ]
        return report

    def _critique(self, report: AnalyticsReport, criteria: List[str], task: List[PieceRecord]) -> Critique:
        issues: List[Issue] = []
        if report.avg_traction == 0.0 and task:
            issues.append(Issue("north-star", "traction/ROI not reported (vanity: views only)", "major"))
        if not report.roi_by_format and task:
            issues.append(Issue("breakdown", "no ROI-by-format / hook breakdown", "major"))
        if not report.winners and task:
            issues.append(Issue("winners", "winners/losers not identified", "major"))
        return Critique(issues=issues)

    def _revise(
        self, report: AnalyticsReport, critique: Critique, criteria: List[str], task: List[PieceRecord]
    ) -> AnalyticsReport:
        locations = {i.location for i in critique.issues}
        if "north-star" in locations:
            report.avg_traction = _avg([p.traction_score for p in task])
            report.blended_roi = _avg([p.roi for p in task])
            report.leaderboard = [
                {
                    "piece_id": p.piece_id,
                    "topic": p.topic,
                    "traction": p.traction_score,
                    "roi": p.roi,
                    "views": p.views,
                }
                for p in sorted(task, key=lambda p: p.traction_score, reverse=True)[:5]
            ]
        if "breakdown" in locations:
            by_fmt: Dict[str, List[float]] = {}
            by_hook: Dict[str, List[float]] = {}
            for p in task:
                by_fmt.setdefault(p.content_format, []).append(p.roi)
                by_hook.setdefault(p.hook_style, []).append(p.traction_score)
            report.roi_by_format = {k: _avg(v) for k, v in by_fmt.items()}
            report.traction_by_hook = {k: _avg(v) for k, v in by_hook.items()}
        if "winners" in locations:
            ranked = sorted(task, key=lambda p: p.traction_score, reverse=True)
            report.winners = [f"{p.topic} (traction {p.traction_score:.2f})" for p in ranked[:2]]
            report.losers = [f"{p.topic} (traction {p.traction_score:.2f})" for p in ranked[-2:]]
        return report
