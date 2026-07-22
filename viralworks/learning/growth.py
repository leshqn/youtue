"""The Self-Growth Engine — the heart of the company.

Each Growth Cycle:
  1. Correlates features (hook style, format, length, post time) with traction.
  2. Extracts concrete, evidence-backed playbook updates — but only those that
     survive validation on a held-out split (guards against learning from noise).
  3. Rewrites the per-niche playbook heuristics (versioned; history kept on disk
     and in the store — never silently overwritten).
  4. Has HR act on the roster and Strategy reset objectives.
  5. Logs a short Growth Report: what changed, why, expected impact.

The A/B/holdout mechanism is what makes "always growing" real rather than vibes:
a candidate learning is found on the training split and must also beat the field
on the holdout split by a minimum lift before it is adopted.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from statistics import mean, pstdev
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..agents.analytics import AnalyticsAgent, AnalyticsReport
from ..agents.base import AgentContext
from ..agents.hr import HRAgent
from ..agents.strategy import StrategyAgent
from ..contracts import GrowthReport, Learning, PieceRecord
from ..utils import slug

MIN_PIECES = 6          # need at least this many pieces to attempt learning
MIN_TRAIN_GROUP = 3     # a candidate needs >= this many training samples
MIN_HOLD_GROUP = 2      # ... and >= this many on each side of the holdout test
MIN_HOLDOUT_LIFT = 0.03 # minimum absolute holdout lift over the field
Z_MIN = 1.0             # minimum z-score of the holdout two-sample difference


def _length_bucket(p: PieceRecord) -> int:
    return int(round(p.length_sec / 4.0)) * 4


class GrowthEngine:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx
        self.store = ctx.store

    # --- validated learning ------------------------------------------------ #
    def _validated_best(
        self,
        train: List[PieceRecord],
        holdout: List[PieceRecord],
        key_fn: Callable[[PieceRecord], Any],
        dimension: str,
        niche: str,
    ) -> Optional[Tuple[Any, Learning]]:
        """Find the best value on train, then run a two-sample z-test on the holdout.

        The candidate (best mean on the *training* split, with enough support) is
        adopted only if, on the *held-out* split, its traction beats the rest of
        the field by a statistically meaningful margin (z >= ``Z_MIN`` and an
        absolute lift >= ``MIN_HOLDOUT_LIFT``). The z-test scales with sample size
        and noise, so strong effects pass early while weak/noisy ones are refused
        until (if ever) enough evidence accrues — no learning from noise.
        """
        def grouped(pieces: List[PieceRecord]) -> Dict[Any, List[float]]:
            g: Dict[Any, List[float]] = {}
            for p in pieces:
                g.setdefault(key_fn(p), []).append(p.traction_score)
            return g

        train_groups = grouped(train)
        train_means = {k: mean(v) for k, v in train_groups.items() if len(v) >= MIN_TRAIN_GROUP}
        if not train_means:
            return None
        best = max(train_means, key=lambda k: train_means[k])

        best_hold = [p.traction_score for p in holdout if key_fn(p) == best]
        rest_hold = [p.traction_score for p in holdout if key_fn(p) != best]
        if len(best_hold) < MIN_HOLD_GROUP or len(rest_hold) < MIN_HOLD_GROUP:
            return None

        lift = round(mean(best_hold) - mean(rest_hold), 4)
        pooled = pstdev(best_hold + rest_hold) or 1e-9
        se = pooled * ((1 / len(best_hold) + 1 / len(rest_hold)) ** 0.5)
        z = lift / se if se else 0.0
        if lift < MIN_HOLDOUT_LIFT or z < Z_MIN:
            return None  # not statistically distinguishable from noise

        confidence = round(min(1.0, z / 3.0), 3)
        learning = Learning(
            dimension=dimension,
            finding=f"'{best}' is the top {dimension} in {niche}.",
            recommendation=f"Default {dimension} -> '{best}'.",
            evidence=(
                f"train mean {train_means[best]:.3f} (n={len(train_groups[best])}); "
                f"holdout lift +{lift:.3f} (z={z:.1f}, n={len(best_hold)}v{len(rest_hold)})."
            ),
            lift=lift,
            confidence=confidence,
            applies_to_niche=niche,
        )
        return best, learning

    def _extract_learnings(
        self, niche: str, pieces: List[PieceRecord]
    ) -> Tuple[Dict[str, Any], List[Learning]]:
        """Return (heuristic_updates, learnings) validated on a holdout split."""
        train = [p for p in pieces if not p.is_holdout]
        holdout = [p for p in pieces if p.is_holdout]
        updates: Dict[str, Any] = {}
        learnings: List[Learning] = []
        if len(train) < MIN_TRAIN_GROUP or len(holdout) < MIN_HOLD_GROUP:
            return updates, learnings

        dims = [
            (lambda p: p.hook_style, "hook_style", "default_hook_style"),
            (lambda p: p.content_format, "content_format", "preferred_formats"),
            (_length_bucket, "length_sec", "target_length_sec"),
            (lambda p: p.post_hour, "post_hour", "best_post_hour"),
        ]
        for key_fn, dim, heuristic_key in dims:
            found = self._validated_best(train, holdout, key_fn, dim, niche)
            if not found:
                continue
            best, learning = found
            learnings.append(learning)
            if heuristic_key == "preferred_formats":
                # Order formats by train performance, validated winner first.
                by_fmt: Dict[str, List[float]] = {}
                for p in train:
                    by_fmt.setdefault(p.content_format, []).append(p.traction_score)
                ordered = sorted(by_fmt, key=lambda k: mean(by_fmt[k]), reverse=True)
                updates[heuristic_key] = ([best] + [f for f in ordered if f != best])[:3]
            elif heuristic_key == "target_length_sec":
                updates[heuristic_key] = float(best)
            else:
                updates[heuristic_key] = best
        return updates, learnings

    # --- playbook persistence (versioned, history kept) -------------------- #
    def _write_playbook_file(
        self, niche: str, version: int, heuristics: Dict[str, Any], learnings: List[Learning]
    ) -> None:
        d = self.ctx.config.playbooks_dir / slug(niche)
        d.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Playbook — {niche} — v{version}",
            f"_generated: {time.strftime('%Y-%m-%d %H:%M:%S')}_",
            "",
            "## Active heuristics",
            "```json",
            json.dumps(heuristics, indent=2),
            "```",
            "",
            "## Learnings adopted this version",
        ]
        if learnings:
            for l in learnings:
                lines.append(
                    f"- **{l.dimension}**: {l.recommendation} "
                    f"(lift +{l.lift:.3f}, confidence {l.confidence:.2f}) — {l.evidence}"
                )
        else:
            lines.append("- None validated this cycle (held existing playbook).")
        (d / f"v{version:03d}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- the cycle --------------------------------------------------------- #
    def run_cycle(self, niche: str, cycle: int, model_calls: int = 0) -> GrowthReport:
        pieces = self.store.pieces(niche=niche)
        analytics_agent = AnalyticsAgent(self.ctx)
        hr_agent = HRAgent(self.ctx)
        strategy_agent = StrategyAgent(self.ctx)

        # Analytics report over this cycle's pieces (loop-engineered, no vanity metrics).
        this_cycle = [p for p in pieces if p.cycle == cycle]
        analytics: AnalyticsReport = analytics_agent.run(this_cycle).output

        # Extract + validate learnings across all pieces for the niche.
        if len(pieces) >= MIN_PIECES:
            updates, learnings = self._extract_learnings(niche, pieces)
        else:
            updates, learnings = {}, []

        # Build and persist the new playbook version.
        current = self.store.playbook_heuristics(niche)
        new_heuristics = dict(current)
        new_heuristics.update(updates)
        # Mark validated dimensions (monotonic) so agents switch from exploring to
        # exploiting them, while never un-learning a previously validated edge.
        validated = set(current.get("validated_dims", []))
        validated.update(l.dimension for l in learnings)
        new_heuristics["validated_dims"] = sorted(validated)
        new_heuristics["notes"] = (
            [l.recommendation for l in learnings]
            if learnings
            else (
                ["Gathering data — not enough pieces to validate learnings yet."]
                if len(pieces) < MIN_PIECES
                else ["No learning beat the holdout this cycle — held existing playbook."]
            )
        )
        version = self.store.save_playbook(niche, new_heuristics, learnings)
        self._write_playbook_file(niche, version, new_heuristics, learnings)

        # HR acts on the roster; Strategy resets the objective.
        hr_report = hr_agent.run({"cycle": cycle, "pieces": this_cycle}).output
        strategy_report = strategy_agent.run(
            {
                "cycle": cycle,
                "niche": niche,
                "analytics": analytics,
                "hr": hr_report,
                "target": self.ctx.config.reels_per_week_target,
            }
        ).output

        validated_lift = round(max((l.lift for l in learnings), default=0.0), 4)
        summary = self._summary(cycle, learnings, analytics, validated_lift)

        report = GrowthReport(
            cycle=cycle,
            pieces_analyzed=len(this_cycle),
            learnings=learnings,
            playbook_version=version,
            roster_changes=hr_report.changes,
            strategy_objective=strategy_report.objective,
            summary=summary,
            validated_lift=validated_lift,
        )
        self.store.save_growth_report(report)
        # Stash the sub-reports for the dashboard.
        self._last_analytics = analytics
        self._last_hr = hr_report
        self._last_strategy = strategy_report
        return report

    def _summary(
        self, cycle: int, learnings: List[Learning], analytics: AnalyticsReport, lift: float
    ) -> str:
        if not learnings:
            return (
                f"Cycle {cycle}: avg traction {analytics.avg_traction:.3f}, "
                f"blended ROI {analytics.blended_roi:.2f}. No validated learning this cycle."
            )
        changes = "; ".join(f"{l.dimension}->{l.recommendation.split('->')[-1].strip().rstrip('.')}" for l in learnings)
        return (
            f"Cycle {cycle}: avg traction {analytics.avg_traction:.3f}, "
            f"blended ROI {analytics.blended_roi:.2f}. Adopted {len(learnings)} "
            f"validated learning(s) [{changes}] with max holdout lift +{lift:.3f}."
        )
