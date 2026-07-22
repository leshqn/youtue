"""Department 4 — Brand Safety & QA ("Quality/Legal").

Gatekeeper before publish. Checks platform ToS compliance, copyright/music
licensing risk, misleading claims, brand-voice consistency, and "would this
embarrass us." Can block or return with notes. This is the mandatory
human-in-the-loop checkpoint (``requires_human_review`` is always True).
"""

from __future__ import annotations

from typing import Any, List

from ..contracts import QAReport, ReelSpec
from ..loop_engine import Critique, Issue
from .base import Agent

_CLAIM_TERMS = [
    "guaranteed", "cure", "get rich", "100%", "overnight", "miracle",
    "lose weight fast", "risk-free", "instantly rich",
]
_BANNED_TAGS = ["#followforfollow", "#f4f", "#likeforlike", "#l4l", "#follow4follow", "#sub4sub"]
_SAFE_AUDIO_HINTS = ["licensed", "original", "royalty"]


class QAAgent(Agent):
    name = "Quality/Legal"
    role = "gatekeep brand safety, ToS, licensing and misleading claims before publish"
    kpis = ["blocked-risk catch rate", "false-block rate", "brand-voice consistency"]
    failure_modes = ["missed copyright risk", "missed misleading claim", "over-blocking"]

    def _criteria(self, task: ReelSpec) -> List[str]:
        return [
            "no unlicensed-music risk left unflagged",
            "no misleading or harmful claims in caption OR voiceover",
            "no ToS-violating hashtags (engagement-baiting)",
            "brand-voice consistent; caption present",
            "human review required before any publish",
        ]

    def _scan_text(self, text: str) -> List[str]:
        low = text.lower()
        return [term for term in _CLAIM_TERMS if term in low]

    def _draft(self, task: ReelSpec, criteria: List[str]) -> QAReport:
        blocks: List[str] = []
        notes: List[str] = []
        risks: List[str] = []

        # Music licensing.
        if not any(h in task.audio_track.lower() for h in _SAFE_AUDIO_HINTS):
            risks.append(f"Confirm commercial license for audio '{task.audio_track}'.")

        # Misleading claims (caption first; voiceover scanned in the loop's revise).
        for term in self._scan_text(task.caption):
            blocks.append(f"Misleading/absolute claim in caption: '{term}'.")

        # ToS hashtags.
        for tag in task.hashtags:
            if tag.lower() in _BANNED_TAGS:
                blocks.append(f"Engagement-baiting hashtag violates ToS: {tag}.")

        # Brand voice / completeness.
        if not task.caption.strip():
            blocks.append("Empty caption — off-brand and incomplete.")

        return QAReport(
            spec_id=task.spec_id,
            approved=len(blocks) == 0,
            blocks=blocks,
            notes=notes,
            risk_flags=risks,
            requires_human_review=True,
        )

    def _critique(self, report: QAReport, criteria: List[str], task: ReelSpec) -> Critique:
        issues: List[Issue] = []
        # Known blind spot: the first pass only scanned the caption, not the
        # spoken script. Force a voiceover claim scan.
        vo_text = " ".join(s.get("voiceover", "") for s in task.storyboard)
        if self._scan_text(vo_text) and not any("voiceover" in b for b in report.blocks):
            issues.append(Issue("claims", "voiceover not scanned for claims", "major"))
        if not report.requires_human_review:
            issues.append(Issue("human_review", "human review flag missing", "block"))
        return Critique(issues=issues)

    def _revise(
        self, report: QAReport, critique: Critique, criteria: List[str], task: ReelSpec
    ) -> QAReport:
        locations = {i.location for i in critique.issues}
        if "claims" in locations:
            vo_text = " ".join(s.get("voiceover", "") for s in task.storyboard)
            for term in self._scan_text(vo_text):
                report.blocks.append(f"Misleading/absolute claim in voiceover: '{term}'.")
            report.approved = len(report.blocks) == 0
        if "human_review" in locations:
            report.requires_human_review = True
        return report
