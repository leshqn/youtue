"""Department 5 — Distribution & Publishing ("Growth").

Schedules and posts to each platform, picks post times (from the learned best
hour, with occasional exploration so the Growth Engine can keep validating the
best hour), handles per-platform formatting and cross-posting. Auto-publish is an
explicit opt-in (off by default); otherwise posts are queued for human review.
"""

from __future__ import annotations

from typing import Any, List

from ..contracts import PublishResult, ReelSpec
from ..loop_engine import Critique, Issue
from ..utils import jitter, pick, should_explore
from .base import Agent

_HOUR_JITTER = [-2.0, -1.0, 0.0, 2.0, 3.0]
_COLD_HOURS = [9.0, 12.0, 15.0, 18.0, 21.0]


class DistributionAgent(Agent):
    name = "Growth"
    role = "schedule and publish reels per platform at the best time"
    kpis = ["post cadence adherence", "on-time scheduling", "per-platform fit"]
    failure_modes = ["bad timing", "wrong per-platform formatting", "no posting cadence"]

    def _chosen_hour(self, task: ReelSpec) -> int:
        h = self.ctx.heuristics(task.niche)
        # Independent salt so hour exploration doesn't correlate with hook/length.
        seed = f"hour|{self.ctx.cycle}|{task.topic}"
        # Until post_hour is validated, explore hours uniformly (unbiased sample).
        if "post_hour" not in h.get("validated_dims", []):
            return int(pick(seed, _COLD_HOURS))
        base = int(h["best_post_hour"])
        if should_explore(seed):
            base += int(jitter(seed, _HOUR_JITTER))
        return max(0, min(23, base))

    def _criteria(self, task: ReelSpec) -> List[str]:
        return [
            f"a scheduled post for every platform: {self.ctx.config.platforms}",
            "all platforms scheduled at the same chosen hour (consistent cross-posting)",
            "per-platform formatting recorded",
            "auto-publish respects the config flag (off => human review)",
        ]

    def _draft(self, task: ReelSpec, criteria: List[str]) -> PublishResult:
        hour = self._chosen_hour(task)
        auto = self.ctx.config.auto_publish
        posts = {}
        for platform in self.ctx.config.platforms:
            publisher = self.ctx.publishers.get(platform)
            if publisher is None:
                continue
            result = publisher.publish(task, hour, auto)
            result["formatting"] = self._formatting(platform, task)
            posts[platform] = result
        return PublishResult(spec_id=task.spec_id, platform_posts=posts, auto_published=auto)

    def _formatting(self, platform: str, spec: ReelSpec) -> dict:
        # Per-platform caption/hashtag nuances.
        if platform == "youtube_shorts":
            return {"title": spec.caption[:90], "hashtags": spec.hashtags[:3], "shorts": True}
        if platform == "tiktok":
            return {"caption": spec.caption[:150], "hashtags": spec.hashtags[:5]}
        return {"caption": spec.caption[:2200], "hashtags": spec.hashtags[:10]}

    def _critique(self, result: PublishResult, criteria: List[str], task: ReelSpec) -> Critique:
        issues: List[Issue] = []
        hour = self._chosen_hour(task)
        for platform in self.ctx.config.platforms:
            post = result.platform_posts.get(platform)
            if post is None:
                issues.append(Issue(platform, "platform not scheduled", "major"))
                continue
            if post.get("scheduled_hour") != hour:
                issues.append(Issue(platform, "hour inconsistent across platforms", "major"))
            if "formatting" not in post:
                issues.append(Issue(platform, "missing per-platform formatting", "minor"))
        return Critique(issues=issues)

    def _revise(
        self, result: PublishResult, critique: Critique, criteria: List[str], task: ReelSpec
    ) -> PublishResult:
        hour = self._chosen_hour(task)
        for platform in self.ctx.config.platforms:
            publisher = self.ctx.publishers.get(platform)
            if publisher is None:
                continue
            post = result.platform_posts.get(platform)
            if post is None or post.get("scheduled_hour") != hour or "formatting" not in post:
                fixed = publisher.publish(task, hour, self.ctx.config.auto_publish)
                fixed["formatting"] = self._formatting(platform, task)
                result.platform_posts[platform] = fixed
        return result
