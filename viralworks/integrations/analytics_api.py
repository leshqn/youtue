"""Analytics source — stub 'world model' + live slot.

The stub is the crux of the self-growth demonstration. Real platforms have hidden
rules about what performs; here we encode a deterministic per-niche hidden
preference function (best hook style, length sweet-spot, best post hour, best
format). Realized metrics = signal (match to those hidden prefs) + small
reproducible noise. Because signal dominates noise, the Growth Engine can learn
the real structure and *validate* the lift on a holdout — not learn from noise.

The company never sees these preferences; it must discover them from outcomes.

To go live: implement ``metrics_for`` against platform Insights endpoints and
return the same ``Metrics`` shape.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Dict

from ..contracts import Metrics, ReelSpec

_HOOK_STYLES = ["text", "voiceover", "visual", "question", "stat"]
_FORMATS = ["listicle", "tutorial", "storytime", "reaction", "transformation", "myth_busting"]


def _h(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest(), 16)


def hidden_prefs(niche: str) -> Dict[str, Any]:
    """The (hidden) ground truth for a niche. Deterministic, but unknown to agents."""
    s = _h("prefs", niche)
    return {
        "best_hook_style": _HOOK_STYLES[s % len(_HOOK_STYLES)],
        "best_length_sec": 18 + (s >> 4) % 10,     # 18..27
        "best_post_hour": 17 + (s >> 8) % 6,       # 17..22
        "best_format": _FORMATS[(s >> 12) % len(_FORMATS)],
    }


def _noise(spec_id: str) -> float:
    """Reproducible noise in ~[-0.03, 0.03]. Small vs. the signal band."""
    return ((_h("noise", spec_id) % 1000) / 1000.0 - 0.5) * 0.06


class StubMetricsSource:
    """Deterministic metrics driven by the hidden world model."""

    def __init__(self, base_reach: int = 5000) -> None:
        self.base_reach = base_reach

    def _quality(self, features: Dict[str, Any], seed: str) -> float:
        prefs = hidden_prefs(features["niche"])
        q = 0.50
        # Hook style: the dominant lever (matches the 'text hooks 2:1' narrative).
        q += 0.25 if features["hook_style"] == prefs["best_hook_style"] else -0.06
        # Length: gaussian around the sweet spot (narrow enough to be learnable).
        dl = features["length_sec"] - prefs["best_length_sec"]
        q += 0.15 * math.exp(-(dl * dl) / (2 * 4 * 4)) - 0.05
        # Post hour: gaussian around the best hour.
        dh = features["post_hour"] - prefs["best_post_hour"]
        q += 0.12 * math.exp(-(dh * dh) / (2 * 3 * 3)) - 0.04
        # Format preference.
        q += 0.15 if features["content_format"] == prefs["best_format"] else -0.03
        q += _noise(seed)
        return max(0.02, min(0.98, q))

    def metrics_for(self, spec: ReelSpec, features: Dict[str, Any]) -> Metrics:
        # A stable content seed keeps realized metrics reproducible across runs.
        seed = str(features.get("seed", spec.spec_id))
        q = self._quality(features, seed)
        spread = 0.4 + 1.6 * q
        views = int(self.base_reach * spread * (0.85 + 0.3 * ((_h("v", seed) % 100) / 100)))
        watch_through = round(0.25 + 0.6 * q, 4)
        ctr = round(0.01 + 0.06 * q, 4)
        shares = int(views * (0.002 + 0.02 * q))
        saves = int(views * (0.003 + 0.03 * q))
        comments = int(views * (0.001 + 0.01 * q))
        follows = int(views * (0.0005 + 0.008 * q))
        cost = float(features.get("cost_usd", 0.0)) or 0.35
        return Metrics(
            spec_id=spec.spec_id,
            views=views,
            watch_through=watch_through,
            shares=shares,
            saves=saves,
            comments=comments,
            follows=follows,
            ctr=ctr,
            cost_usd=round(cost, 4),
        )


class LiveMetricsSource:
    """Slot for real platform Insights (IG/TikTok/YouTube analytics)."""

    def __init__(self, integrations) -> None:
        self.integrations = integrations

    def metrics_for(self, spec: ReelSpec, features: Dict[str, Any]) -> Metrics:
        raise NotImplementedError(
            "Pull real per-post insights and map them into the Metrics contract."
        )


def build_metrics_source(integrations) -> StubMetricsSource:
    # When any analytics integration is configured you would return LiveMetricsSource.
    return StubMetricsSource()
