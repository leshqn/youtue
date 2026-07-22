"""Department 2 — Creative & Refinement ("Studio").

Turns an Opportunity into a concrete deliverable: hook, script/VO, beat-by-beat
shot list, on-screen text, pacing, CTA, caption + hashtags. The runtime loop
bites hardest here — the hook and first two seconds are iterated until they are
genuinely scroll-stopping and the runtime fits the (per-piece, learned) target.

Exploit/explore: most pieces use the *learned* winning hook style (so learning
changes produced content); a minority explore the trend-suggested style (so the
Growth Engine keeps getting variance to learn from).
"""

from __future__ import annotations

from typing import Any, List

from ..contracts import CreativeBrief, Opportunity, ShotBeat
from ..loop_engine import Critique, Issue
from ..utils import jitter, pick, should_explore
from .base import Agent

_ALL_HOOK_STYLES = ["text", "voiceover", "visual", "question", "stat"]

# Hook ladders per style, ordered weak -> strong. Revision climbs the ladder.
_HOOK_LADDERS = {
    "text": [
        "Some {niche} tips you might find useful",
        "{n} {niche} mistakes you're probably making",
        "Stop doing this in {niche} — it's quietly costing you",
    ],
    "voiceover": [
        "Today I want to talk about {niche}",
        "Here's what nobody tells you about {niche}",
        "I wasted 2 years on {niche} so you don't have to",
    ],
    "visual": [
        "A clip about {niche}",
        "Watch what happens when you {niche} like this",
        "This {niche} result in 3 seconds will stop your scroll",
    ],
    "question": [
        "Do you do {niche}?",
        "Why is your {niche} not working?",
        "What if everything you knew about {niche} was wrong?",
    ],
    "stat": [
        "Some numbers about {niche}",
        "80% of people get {niche} wrong",
        "92% of people fail at {niche} for this one reason",
    ],
}

_ALL_FORMATS = ["listicle", "tutorial", "storytime", "reaction", "transformation", "myth_busting"]
_STRONG_TRIGGERS = ("stop", "nobody", "wrong", "mistake", "%", "wasted", "secret", "why")
_LENGTH_JITTER = [-4.0, -2.0, 0.0, 2.0, 4.0]
_COLD_LENGTHS = [16.0, 20.0, 24.0, 28.0, 32.0]


class CreativeAgent(Agent):
    name = "Studio"
    role = "refine an opportunity into a scroll-stopping, on-brand reel brief"
    kpis = ["hook strength", "watch-through", "on-brand voice", "runtime discipline"]
    failure_modes = ["weak hook", "buried payoff", "bloated runtime", "off-brand voice"]

    # --- per-piece feature choices (deterministic; enable learning) -------- #
    def _seed(self, task: Opportunity) -> str:
        # Stable per (cycle, topic) so runs are reproducible but each cycle varies.
        return f"{self.ctx.cycle}|{task.topic}"

    def _piece_hook_style(self, task: Opportunity) -> str:
        h = self.ctx.heuristics(task.niche)
        # Per-dimension salt so hook/length/hour exploration are INDEPENDENT
        # (a shared seed would make features collinear and unlearnable).
        seed = "hook|" + self._seed(task)
        # Until hook_style is validated, explore uniformly (unbiased sample).
        if "hook_style" not in h.get("validated_dims", []):
            return pick(seed, _ALL_HOOK_STYLES)
        # Validated: mostly exploit the learned winner, keep an exploration epsilon.
        if should_explore(seed):
            return pick(seed, _ALL_HOOK_STYLES)
        return h["default_hook_style"]

    def _piece_format(self, task: Opportunity) -> str:
        h = self.ctx.heuristics(task.niche)
        seed = "fmt|" + self._seed(task)
        # Explore formats independently until one is validated; then exploit it.
        if "content_format" not in h.get("validated_dims", []):
            return pick(seed, _ALL_FORMATS)
        if should_explore(seed):
            return pick(seed, _ALL_FORMATS)
        return h.get("preferred_formats", _ALL_FORMATS)[0]

    def _piece_target_len(self, task: Opportunity) -> float:
        h = self.ctx.heuristics(task.niche)
        seed = "len|" + self._seed(task)
        # Until length is validated, sample across the range to find the sweet spot.
        if "length_sec" not in h.get("validated_dims", []):
            return pick(seed, _COLD_LENGTHS)
        base = float(h["target_length_sec"])
        if should_explore(seed):
            base += jitter(seed, _LENGTH_JITTER)
        return max(12.0, min(45.0, base))

    def _hook_for(self, style: str, niche: str, rung: int) -> str:
        ladder = _HOOK_LADDERS.get(style, _HOOK_LADDERS["text"])
        rung = max(0, min(rung, len(ladder) - 1))
        return ladder[rung].replace("{niche}", niche).replace("{n}", "3")

    # --- loop hooks -------------------------------------------------------- #
    def _criteria(self, task: Opportunity) -> List[str]:
        target = self._piece_target_len(task)
        return [
            "hook lands in under 2 seconds and is scroll-stopping",
            "a single, clear payoff — no burying the lede",
            f"runtime <= {target:.0f}s (learned target)",
            "on-brand voice and a clear CTA",
            "caption + at least 3 hashtags",
        ]

    def _draft(self, task: Opportunity, criteria: List[str]) -> CreativeBrief:
        niche = task.niche
        style = self._piece_hook_style(task)
        content_format = self._piece_format(task)
        # Honest first attempt: a mid-strength hook and a slightly long runtime.
        hook = self._hook_for(style, niche, rung=1)
        length = self._piece_target_len(task) + 5.0
        cta = "Follow for one more tomorrow."
        script = (
            f"{hook} "
            f"Here's the {content_format} breakdown you actually need for {task.topic}. "
            f"By the end you'll know exactly what to change."
        )
        shots = self._build_shots(hook, task, length)
        fallback_caption = f"{task.topic} — save this. {cta}"
        caption = self._maybe_llm(
            prompt=(
                f"Write a punchy {niche} caption (max 150 chars) for a reel about "
                f"'{task.topic}' ending with a follow CTA. Voice: {self.ctx.config.brand_voice}."
            ),
            fallback=fallback_caption,
        )
        return CreativeBrief(
            opportunity_id=task.opportunity_id,
            topic=task.topic,
            niche=niche,
            content_format=content_format,
            hook=hook,
            hook_style=style,
            script=script,
            shot_list=shots,
            on_screen_text=[hook, "the fix ->", cta],
            cta=cta,
            caption=caption,
            hashtags=task.hashtags,
            length_sec=length,
            pacing="fast",
            trending_sound=task.trending_sound,
        )

    def _build_shots(self, hook: str, task: Opportunity, length: float) -> List[ShotBeat]:
        # Beat 1 is the ~2s hook; the remaining time is split evenly across 3 beats.
        hook_end = min(2.0, length * 0.15)
        rest = (length - hook_end) / 3.0
        b2, b3 = hook_end + rest, hook_end + 2 * rest
        return [
            ShotBeat(0.0, round(hook_end, 2), f"Cold open, bold visual for {task.topic}", hook, hook),
            ShotBeat(round(hook_end, 2), round(b2, 2), "Problem framing, quick cuts", "the mistake", "Most people do this…"),
            ShotBeat(round(b2, 2), round(b3, 2), "The payoff / method reveal", "the fix ->", "Here's the fix."),
            ShotBeat(round(b3, 2), round(length, 2), "Proof + CTA card", "follow for more", "Follow for one more tomorrow."),
        ]

    def _hook_is_strong(self, hook: str) -> bool:
        low = hook.lower()
        return len(hook.split()) <= 12 and any(t in low for t in _STRONG_TRIGGERS)

    def _critique(self, brief: CreativeBrief, criteria: List[str], task: Opportunity) -> Critique:
        issues: List[Issue] = []
        target = self._piece_target_len(task)
        if not self._hook_is_strong(brief.hook):
            issues.append(Issue("hook", "not maximally scroll-stopping (weak or verbose)", "major"))
        if brief.length_sec > target + 2:
            issues.append(
                Issue("runtime", f"{brief.length_sec:.0f}s exceeds target {target:.0f}s", "major")
            )
        if "fix" not in brief.script.lower() and "payoff" not in brief.script.lower():
            issues.append(Issue("payoff", "single clear payoff not obvious", "major"))
        if not brief.cta:
            issues.append(Issue("cta", "missing CTA", "major"))
        if len(brief.hashtags) < 3:
            issues.append(Issue("hashtags", "fewer than 3 hashtags", "minor"))
        return Critique(issues=issues)

    def _revise(
        self, brief: CreativeBrief, critique: Critique, criteria: List[str], task: Opportunity
    ) -> CreativeBrief:
        target = self._piece_target_len(task)
        locations = {i.location for i in critique.issues}
        if "hook" in locations:
            brief.hook = self._hook_for(brief.hook_style, task.niche, rung=99)  # top rung
            brief.on_screen_text[0] = brief.hook
        if "runtime" in locations:
            brief.length_sec = target
            brief.shot_list = self._build_shots(brief.hook, task, target)
        if "payoff" in locations:
            brief.script = f"{brief.hook} The fix: {task.topic}. Do this instead and watch it change."
        if "cta" in locations and not brief.cta:
            brief.cta = "Follow for one more tomorrow."
        if "hashtags" in locations and len(brief.hashtags) < 3:
            brief.hashtags = brief.hashtags + ["#fyp", "#viral"]
        return brief
