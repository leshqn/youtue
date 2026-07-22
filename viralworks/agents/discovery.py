"""Department 1 — Trend & Content Discovery ("R&D").

Scans trend signals and produces a ranked Opportunity Board of content bets with
a 'why now' rationale and a predicted-traction score. Its ranking is shaped by
the *learned* playbook heuristics, so it demonstrably changes behaviour across
cycles.
"""

from __future__ import annotations

from typing import Any, List

from ..contracts import Brief, Opportunity, OpportunityBoard
from ..loop_engine import Critique, Issue
from .base import Agent


class DiscoveryAgent(Agent):
    name = "R&D"
    role = "discover what is trending now and rank content bets by predicted traction"
    kpis = ["predicted-vs-actual traction correlation", "hit rate of top bet", "niche fit"]
    failure_modes = [
        "chasing dead trends",
        "generic topics",
        "ignoring niche fit",
        "duplicate bets",
    ]

    def _criteria(self, task: Brief) -> List[str]:
        h = self.ctx.heuristics(task.niche)
        return [
            "at least 4 distinct, non-duplicate bets",
            "every bet has a concrete, time-bound 'why now'",
            "no generic topics — each names something specific in the niche",
            f"bets fit the niche: {task.niche}",
            f"favour the learned hook style ({h['default_hook_style']}) and "
            f"formats {h['preferred_formats']}",
            "top bet predicted_traction >= 0.5",
        ]

    def _score(self, signal: dict, niche: str) -> float:
        """Predicted traction: raw heat nudged by what the company has learned."""
        h = self.ctx.heuristics(niche)
        score = 0.35 + 0.4 * float(signal.get("heat", 0.0))
        if signal["suggested_hook_style"] == h["default_hook_style"]:
            score += 0.15
        if signal["content_format"] in h["preferred_formats"]:
            score += 0.10
        return score

    def _draft(self, task: Brief, criteria: List[str]) -> OpportunityBoard:
        signals = self.ctx.trend_source.fetch(task.niche, task.platforms)
        opps: List[Opportunity] = []
        for s in signals:
            opps.append(
                Opportunity(
                    topic=s["topic"],
                    niche=task.niche,
                    content_format=s["content_format"],
                    suggested_hook_style=s["suggested_hook_style"],
                    trending_sound=s["trending_sound"],
                    hashtags=s["hashtags"],
                    why_now=(
                        f"'{s['trending_sound']}' is surging on "
                        f"{', '.join(task.platforms)} and heat={s['heat']:.2f} for this angle."
                    ),
                    predicted_traction=self._score(s, task.niche),
                )
            )
        return OpportunityBoard(opportunities=opps)

    def _critique(self, board: OpportunityBoard, criteria: List[str], task: Brief) -> Critique:
        issues: List[Issue] = []
        seen = set()
        for o in board.opportunities:
            key = o.topic.strip().lower()
            if key in seen:
                issues.append(Issue(f"bet '{o.topic}'", "duplicate bet", "major"))
            seen.add(key)
            if task.niche.split()[0].lower() not in o.topic.lower() and "{" not in o.topic:
                # weak niche fit: topic doesn't reference the niche
                issues.append(Issue(f"bet '{o.topic}'", "weak niche fit", "minor"))
            if o.predicted_traction < 0.35:
                issues.append(
                    Issue(f"bet '{o.topic}'", "predicted traction too low (dead trend)", "major")
                )
        distinct = len({o.topic.strip().lower() for o in board.opportunities})
        if distinct < 4:
            issues.append(Issue("board", "fewer than 4 distinct bets", "major"))
        if board.ranked() and board.top().predicted_traction < 0.5:
            issues.append(Issue("top bet", "top bet below 0.5 predicted traction", "major"))
        return Critique(issues=issues)

    def _revise(
        self, board: OpportunityBoard, critique: Critique, criteria: List[str], task: Brief
    ) -> OpportunityBoard:
        h = self.ctx.heuristics(task.niche)
        # Drop duplicates and dead trends; align survivors to learned hook style.
        seen = set()
        kept: List[Opportunity] = []
        for o in board.ranked():
            key = o.topic.strip().lower()
            if key in seen or o.predicted_traction < 0.35:
                continue
            seen.add(key)
            # Nudge the strongest bets toward the learned winning hook style.
            if o.predicted_traction >= 0.5 and o.suggested_hook_style != h["default_hook_style"]:
                o.suggested_hook_style = h["default_hook_style"]
                o.predicted_traction = min(1.0, o.predicted_traction + 0.05)
            kept.append(o)
        # If pruning left us thin, keep the best originals to satisfy the >=4 rule.
        if len(kept) < 4:
            for o in board.ranked():
                if o not in kept:
                    kept.append(o)
                if len(kept) >= 4:
                    break
        return OpportunityBoard(opportunities=kept)
