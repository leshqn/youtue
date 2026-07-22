"""Typed contracts passed between departments.

Every handoff in the assembly line is a structured object so departments can be
built and tested in isolation. Implemented with stdlib dataclasses (no external
dependency) plus light runtime validation.

Pipeline data flow::

    Brief
      -> Opportunity (Discovery)
      -> CreativeBrief (Creative)
      -> ReelSpec (Production)
      -> QAReport (QA)
      -> PublishResult (Distribution)
      -> Metrics (Analytics)
      -> PieceRecord (Learning Store)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def now_ts() -> float:
    return time.time()


class HookStyle(str, Enum):
    """The families of opening hooks we can A/B and learn over."""

    TEXT = "text"          # on-screen text hook, no talking
    VO = "voiceover"       # spoken hook
    VISUAL = "visual"      # striking cold-open shot
    QUESTION = "question"  # provocative question
    STAT = "stat"          # surprising statistic


class ContentFormat(str, Enum):
    LISTICLE = "listicle"
    TUTORIAL = "tutorial"
    STORYTIME = "storytime"
    REACTION = "reaction"
    TRANSFORMATION = "transformation"
    MYTH_BUSTING = "myth_busting"


# --------------------------------------------------------------------------- #
# Inbound brief
# --------------------------------------------------------------------------- #
@dataclass
class Brief:
    """The top-level order that kicks off one reel through the pipeline."""

    niche: str
    brand_voice: str
    platforms: List[str]
    goal: str = "maximize traction + monetization"
    seed_topic: Optional[str] = None
    brief_id: str = field(default_factory=lambda: new_id("brief"))
    created_at: float = field(default_factory=now_ts)


# --------------------------------------------------------------------------- #
# Discovery output
# --------------------------------------------------------------------------- #
@dataclass
class Opportunity:
    """A single content bet from the Opportunity Board."""

    topic: str
    niche: str
    content_format: str          # ContentFormat value
    suggested_hook_style: str    # HookStyle value
    trending_sound: str
    hashtags: List[str]
    why_now: str
    predicted_traction: float    # 0..1
    opportunity_id: str = field(default_factory=lambda: new_id("opp"))

    def __post_init__(self) -> None:
        self.predicted_traction = max(0.0, min(1.0, float(self.predicted_traction)))


@dataclass
class OpportunityBoard:
    opportunities: List[Opportunity]
    generated_at: float = field(default_factory=now_ts)

    def ranked(self) -> List[Opportunity]:
        return sorted(
            self.opportunities, key=lambda o: o.predicted_traction, reverse=True
        )

    def top(self) -> Opportunity:
        return self.ranked()[0]


# --------------------------------------------------------------------------- #
# Creative output
# --------------------------------------------------------------------------- #
@dataclass
class ShotBeat:
    t_start: float
    t_end: float
    visual: str
    on_screen_text: str
    voiceover: str


@dataclass
class CreativeBrief:
    opportunity_id: str
    topic: str
    niche: str
    content_format: str
    hook: str
    hook_style: str
    script: str
    shot_list: List[ShotBeat]
    on_screen_text: List[str]
    cta: str
    caption: str
    hashtags: List[str]
    length_sec: float
    pacing: str = "fast"
    trending_sound: str = ""
    creative_id: str = field(default_factory=lambda: new_id("cre"))


# --------------------------------------------------------------------------- #
# Production output
# --------------------------------------------------------------------------- #
@dataclass
class ReelSpec:
    """A render-ready specification (or a real render handle when wired)."""

    creative_id: str
    topic: str
    niche: str
    aspect_ratio: str
    length_sec: float
    caption: str
    hashtags: List[str]
    audio_track: str
    render_prompts: List[str]
    storyboard: List[Dict[str, Any]]
    captions_srt: str
    render_job_id: Optional[str] = None   # set when a real provider renders
    render_url: Optional[str] = None
    est_cost_usd: float = 0.0
    spec_id: str = field(default_factory=lambda: new_id("spec"))


# --------------------------------------------------------------------------- #
# QA output
# --------------------------------------------------------------------------- #
@dataclass
class QAReport:
    spec_id: str
    approved: bool
    blocks: List[str]           # hard blockers (must fix before publish)
    notes: List[str]            # soft notes / suggestions
    risk_flags: List[str]       # copyright, ToS, claims, brand-voice
    requires_human_review: bool = True
    qa_id: str = field(default_factory=lambda: new_id("qa"))


# --------------------------------------------------------------------------- #
# Distribution output
# --------------------------------------------------------------------------- #
@dataclass
class PublishResult:
    spec_id: str
    platform_posts: Dict[str, Dict[str, Any]]  # platform -> {status, scheduled_time,...}
    auto_published: bool
    publish_id: str = field(default_factory=lambda: new_id("pub"))


# --------------------------------------------------------------------------- #
# Analytics output
# --------------------------------------------------------------------------- #
@dataclass
class Metrics:
    spec_id: str
    views: int
    watch_through: float        # 0..1 avg % watched
    shares: int
    saves: int
    comments: int
    follows: int
    ctr: float                  # 0..1
    cost_usd: float

    @property
    def follows_per_view(self) -> float:
        return self.follows / self.views if self.views else 0.0

    @property
    def engagement_rate(self) -> float:
        if not self.views:
            return 0.0
        return (self.shares + self.saves + self.comments) / self.views

    @property
    def traction_score(self) -> float:
        """Blended north-star score in ~0..1 (watch-through, shares, saves, follows)."""
        return round(
            0.40 * self.watch_through
            + 0.20 * min(1.0, self.engagement_rate * 20)
            + 0.20 * min(1.0, self.follows_per_view * 100)
            + 0.20 * min(1.0, self.ctr * 5),
            4,
        )

    @property
    def roi(self) -> float:
        """Value-per-dollar proxy: traction-weighted views per dollar spent."""
        if self.cost_usd <= 0:
            return 0.0
        value = self.views * self.traction_score
        return round(value / self.cost_usd, 2)


# --------------------------------------------------------------------------- #
# Persistent record
# --------------------------------------------------------------------------- #
@dataclass
class PieceRecord:
    """Everything we know about one shipped piece — the unit the company learns from."""

    piece_id: str
    cycle: int
    niche: str
    topic: str
    content_format: str
    hook_style: str
    length_sec: float
    post_hour: int
    why_now: str
    predicted_traction: float
    cost_usd: float
    # populated once metrics arrive
    views: int = 0
    watch_through: float = 0.0
    traction_score: float = 0.0
    roi: float = 0.0
    is_holdout: bool = False
    created_at: float = field(default_factory=now_ts)

    def to_row(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Growth output
# --------------------------------------------------------------------------- #
@dataclass
class Learning:
    """A single evidence-backed playbook update."""

    dimension: str      # e.g. "hook_style", "length_sec", "post_hour"
    finding: str        # human-readable
    recommendation: str # concrete directive an agent can act on
    evidence: str       # the numbers behind it
    lift: float         # measured improvement of the winner vs. field
    confidence: float   # 0..1, validated on holdout
    applies_to_niche: str


@dataclass
class GrowthReport:
    cycle: int
    pieces_analyzed: int
    learnings: List[Learning]
    playbook_version: int
    roster_changes: List[str]
    strategy_objective: str
    summary: str
    validated_lift: float           # holdout-validated lift this cycle
    generated_at: float = field(default_factory=now_ts)


# --------------------------------------------------------------------------- #
# The bundle that flows through the whole pipeline for one piece
# --------------------------------------------------------------------------- #
@dataclass
class PipelineResult:
    brief: Brief
    opportunity: Opportunity
    creative: CreativeBrief
    spec: ReelSpec
    qa: QAReport
    publish: Optional[PublishResult]
    metrics: Optional[Metrics]
    loop_transcripts: Dict[str, Any] = field(default_factory=dict)
    piece_id: str = field(default_factory=lambda: new_id("piece"))
