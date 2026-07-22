"""Department 3 — Production ("The Factory").

Turns the refined brief into a finished reel spec / render job: exact prompts,
assets, timings, captions, and audio. Calls the video provider when wired;
otherwise ships a complete, render-ready spec + storyboard. The loop guards
against spec drift, missing captions, and wrong aspect ratio/length.
"""

from __future__ import annotations

from typing import Any, List

from ..contracts import CreativeBrief, ReelSpec
from ..loop_engine import Critique, Issue
from .base import Agent

_ASPECT = "9:16"


def _fmt_ts(t: float) -> str:
    m, s = divmod(int(t), 60)
    ms = int((t - int(t)) * 1000)
    return f"00:{m:02d}:{s:02d},{ms:03d}"


class ProductionAgent(Agent):
    name = "Factory"
    role = "turn a creative brief into a render-ready reel spec (or a real render)"
    kpis = ["spec fidelity to brief", "caption completeness", "correct format/length"]
    failure_modes = ["spec drift from brief", "missing captions", "wrong aspect ratio/length"]

    def _criteria(self, task: CreativeBrief) -> List[str]:
        return [
            f"vertical {_ASPECT} aspect ratio",
            f"length matches the brief ({task.length_sec:.0f}s)",
            "a render prompt for every shot beat",
            "burned-in captions (SRT) present",
            "caption + hashtags carried faithfully from the brief (no drift)",
        ]

    def _build_srt(self, brief: CreativeBrief) -> str:
        lines = []
        for i, beat in enumerate(brief.shot_list, start=1):
            lines.append(str(i))
            lines.append(f"{_fmt_ts(beat.t_start)} --> {_fmt_ts(beat.t_end)}")
            lines.append(beat.on_screen_text or beat.voiceover)
            lines.append("")
        return "\n".join(lines).strip()

    def _prompts(self, brief: CreativeBrief) -> List[str]:
        return [
            f"{beat.visual}; on-screen text '{beat.on_screen_text}'; "
            f"{brief.pacing} pacing; vertical {_ASPECT}"
            for beat in brief.shot_list
        ]

    def _draft(self, task: CreativeBrief, criteria: List[str]) -> ReelSpec:
        est_cost = round(0.10 + 0.01 * task.length_sec, 4)
        spec = ReelSpec(
            creative_id=task.creative_id,
            topic=task.topic,
            niche=task.niche,
            aspect_ratio=_ASPECT,
            length_sec=task.length_sec,
            caption=task.caption,
            hashtags=task.hashtags,
            audio_track=task.trending_sound or "trending-audio",
            render_prompts=self._prompts(task),
            storyboard=[
                {
                    "t_start": b.t_start,
                    "t_end": b.t_end,
                    "visual": b.visual,
                    "on_screen_text": b.on_screen_text,
                    "voiceover": b.voiceover,
                }
                for b in task.shot_list
            ],
            captions_srt=self._build_srt(task),
            est_cost_usd=est_cost,
        )
        # Call the (stub or live) video provider.
        result = self.ctx.video_generator.render(spec)
        spec.render_job_id = result.get("job_id")
        spec.render_url = result.get("url")
        spec.est_cost_usd = round(est_cost + float(result.get("cost_usd", 0.0)), 4)
        return spec

    def _critique(self, spec: ReelSpec, criteria: List[str], task: CreativeBrief) -> Critique:
        issues: List[Issue] = []
        if spec.aspect_ratio != _ASPECT:
            issues.append(Issue("aspect_ratio", f"not {_ASPECT}", "block"))
        if abs(spec.length_sec - task.length_sec) > 0.5:
            issues.append(Issue("length", "length drifted from brief", "major"))
        if len(spec.render_prompts) != len(task.shot_list):
            issues.append(Issue("render_prompts", "prompt count != shot count", "major"))
        if not spec.captions_srt.strip():
            issues.append(Issue("captions", "missing burned-in captions", "block"))
        if task.caption != spec.caption or task.hashtags != spec.hashtags:
            issues.append(Issue("caption", "spec drifted from brief caption/hashtags", "major"))
        return Critique(issues=issues)

    def _revise(
        self, spec: ReelSpec, critique: Critique, criteria: List[str], task: CreativeBrief
    ) -> ReelSpec:
        locations = {i.location for i in critique.issues}
        if "aspect_ratio" in locations:
            spec.aspect_ratio = _ASPECT
        if "length" in locations:
            spec.length_sec = task.length_sec
        if "render_prompts" in locations:
            spec.render_prompts = self._prompts(task)
        if "captions" in locations:
            spec.captions_srt = self._build_srt(task)
        if "caption" in locations:
            spec.caption = task.caption
            spec.hashtags = task.hashtags
        return spec
