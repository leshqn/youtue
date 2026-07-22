"""Small shared helpers: deterministic exploration and formatting."""

from __future__ import annotations

import hashlib
from typing import List, TypeVar

T = TypeVar("T")


def _hash01(seed: str) -> float:
    """Deterministic float in [0, 1) from a seed string."""
    return (int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 10_000) / 10_000.0


def should_explore(seed: str, explore_prob: float = 0.4) -> bool:
    """Deterministic explore/exploit decision.

    Exploration keeps feature variance alive across pieces so the Growth Engine
    always has fresh signal to validate learnings against (otherwise the company
    would collapse onto one choice and stop being able to learn).
    """
    return _hash01("explore|" + seed) < explore_prob


def pick(seed: str, options: List[T]) -> T:
    """Deterministically pick one option from a list."""
    if not options:
        raise ValueError("cannot pick from empty options")
    idx = int(_hash01("pick|" + seed) * len(options)) % len(options)
    return options[idx]


def jitter(seed: str, choices: List[float]) -> float:
    """Deterministically pick a jitter offset."""
    return pick("jitter|" + seed, choices)


def is_holdout(piece_id: str, frac: float = 0.3) -> bool:
    """Deterministic holdout membership for A/B validation of learnings."""
    return _hash01("holdout|" + piece_id) < frac


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")
