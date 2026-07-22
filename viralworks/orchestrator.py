"""The Orchestrator ("CEO + COO").

Owns the pipeline: assigns briefs, routes work between departments, enforces the
assembly line and the guardrails (QA gate + human-in-the-loop before publish),
runs the Self-Growth Engine at the end of each cycle, and reports what shipped.

Assembly line::

    Discovery -> Creative -> Production -> QA -> Distribution -> Analytics
             -> [Self-Growth Engine: Analytics + HR + Strategy] -> new playbook
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import List, Optional

from .agents import (
    AnalyticsAgent,
    AnalyticsReport,
    CreativeAgent,
    DiscoveryAgent,
    DistributionAgent,
    OpsAgent,
    OpsReport,
    ProductionAgent,
    QAAgent,
)
from .agents.base import AgentContext
from .config import Config
from .contracts import (
    Brief,
    GrowthReport,
    Opportunity,
    PieceRecord,
    PipelineResult,
    new_id,
)
from .integrations import (
    build_metrics_source,
    build_publisher,
    build_trend_source,
    build_video_generator,
)
from .learning.growth import GrowthEngine
from .learning.store import LearningStore, build_store
from .llm.client import ModelClient
from .utils import is_holdout


@dataclass
class CycleResult:
    cycle: int
    niche: str
    pieces: List[PieceRecord]
    blocked: int
    sample: Optional[PipelineResult]
    analytics: AnalyticsReport
    growth: GrowthReport
    ops: OpsReport
    llm_calls: int
    llm_cost_usd: float
    board: List[Opportunity] = field(default_factory=list)
    heuristics_used: dict = field(default_factory=dict)

    @property
    def avg_traction(self) -> float:
        return round(mean(p.traction_score for p in self.pieces), 4) if self.pieces else 0.0

    @property
    def total_cost_usd(self) -> float:
        return round(sum(p.cost_usd for p in self.pieces), 4)


class Orchestrator:
    def __init__(self, config: Config, store: Optional[LearningStore] = None) -> None:
        self.config = config
        config.ensure_dirs()
        self.store = store or build_store(config.learning_store, config.db_path)
        self.model = ModelClient(
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=config.llm.api_key,
        )

    # --- context ----------------------------------------------------------- #
    def _context(self, cycle: int) -> AgentContext:
        publishers = {
            p: build_publisher(p, self.config.integrations) for p in self.config.platforms
        }
        return AgentContext(
            config=self.config,
            model=self.model,
            store=self.store,
            cycle=cycle,
            trend_source=build_trend_source(
                self.config.integrations.trend_data_source, salt=f"cycle-{cycle}"
            ),
            video_generator=build_video_generator(
                self.config.video_generation.provider, self.config.video_generation.api_key
            ),
            metrics_source=build_metrics_source(self.config.integrations),
            publishers=publishers,
        )

    # --- one full cycle ---------------------------------------------------- #
    def run_cycle(self) -> CycleResult:
        cycle = self.store.next_cycle()
        ctx = self._context(cycle)
        # Snapshot the heuristics the agents will USE this cycle (proves evolution).
        heuristics_used = dict(self.store.playbook_heuristics(self.config.niche))
        brief = Brief(
            niche=self.config.niche,
            brand_voice=self.config.brand_voice,
            platforms=self.config.platforms,
            goal=self.config.primary_goal,
        )

        discovery = DiscoveryAgent(ctx)
        creative = CreativeAgent(ctx)
        production = ProductionAgent(ctx)
        qa = QAAgent(ctx)
        distribution = DistributionAgent(ctx)
        analytics = AnalyticsAgent(ctx)

        # 1) Discovery once per cycle -> Opportunity Board.
        board_res = discovery.run(brief)
        board = board_res.output
        n = min(self.config.reels_per_week_target, len(board.opportunities))
        selected = board.ranked()[:n]

        blocked = 0
        sample: Optional[PipelineResult] = None

        # 2) Fan out each opportunity through the assembly line.
        for opp in selected:
            cre_res = creative.run(opp)
            cbrief = cre_res.output
            prod_res = production.run(cbrief)
            spec = prod_res.output
            qa_res = qa.run(spec)
            qreport = qa_res.output

            # Guardrail: CEO does not ship what QA blocked.
            if not qreport.approved:
                blocked += 1
                continue

            dist_res = distribution.run(spec)
            publish = dist_res.output
            post_hour = next(
                (p.get("scheduled_hour", 18) for p in publish.platform_posts.values()), 18
            )

            seed = f"{cycle}|{opp.topic}"
            features = {
                "niche": opp.niche,
                "hook_style": cbrief.hook_style,
                "length_sec": spec.length_sec,
                "post_hour": post_hour,
                "content_format": cbrief.content_format,
                "cost_usd": spec.est_cost_usd,
                "seed": seed,
            }
            metrics = analytics.measure(spec, features)

            piece_id = new_id("piece")
            record = PieceRecord(
                piece_id=piece_id,
                cycle=cycle,
                niche=opp.niche,
                topic=opp.topic,
                content_format=cbrief.content_format,
                hook_style=cbrief.hook_style,
                length_sec=spec.length_sec,
                post_hour=post_hour,
                why_now=opp.why_now,
                predicted_traction=opp.predicted_traction,
                cost_usd=metrics.cost_usd,
                views=metrics.views,
                watch_through=metrics.watch_through,
                traction_score=metrics.traction_score,
                roi=metrics.roi,
                is_holdout=is_holdout(seed),
            )
            self.store.add_piece(record)

            if sample is None:
                sample = PipelineResult(
                    brief=brief,
                    opportunity=opp,
                    creative=cbrief,
                    spec=spec,
                    qa=qreport,
                    publish=publish,
                    metrics=metrics,
                    piece_id=piece_id,
                    loop_transcripts={
                        "R&D": board_res.transcript(),
                        "Studio": cre_res.transcript(),
                        "Factory": prod_res.transcript(),
                        "Quality/Legal": qa_res.transcript(),
                        "Growth": dist_res.transcript(),
                    },
                )

        pieces = self.store.pieces(cycle=cycle)

        # 3) Self-Growth Engine (Analytics + validated learning + HR + Strategy).
        growth_engine = GrowthEngine(ctx)
        growth = growth_engine.run_cycle(
            self.config.niche, cycle, model_calls=self.model.total_calls
        )
        analytics_report = growth_engine._last_analytics

        # 4) Ops report (throughput + cost + bottleneck).
        ops = OpsAgent(ctx).run(
            {
                "cycle": cycle,
                "reels_produced": len(pieces),
                "target": self.config.reels_per_week_target,
                "total_cost_usd": sum(p.cost_usd for p in pieces),
                "model_calls": self.model.total_calls,
            }
        ).output

        return CycleResult(
            cycle=cycle,
            niche=self.config.niche,
            pieces=pieces,
            blocked=blocked,
            sample=sample,
            analytics=analytics_report,
            growth=growth,
            ops=ops,
            llm_calls=self.model.total_calls,
            llm_cost_usd=self.model.total_cost_usd,
            board=board.ranked(),
            heuristics_used=heuristics_used,
        )

    def run_cycles(self, n: int) -> List[CycleResult]:
        return [self.run_cycle() for _ in range(n)]
