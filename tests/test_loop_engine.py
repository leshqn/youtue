"""Unit tests for the shared loop engine."""

import pytest

from viralworks.loop_engine import Critique, Issue, LoopEngine


def test_converges_early_when_critique_passes():
    """A draft with no material issues stops after one pass."""
    engine = LoopEngine(max_passes=4)
    result = engine.run(
        task=0,
        criteria_fn=lambda t: ["be non-negative"],
        draft_fn=lambda t, c: 10,
        critique_fn=lambda o, c, t: Critique(issues=[]),
        revise_fn=lambda o, cr, c, t: o,
    )
    assert result.converged is True
    assert result.num_passes == 1
    assert result.output == 10


def test_revise_repairs_named_weakness_and_converges():
    """The loop should call revise until the named weakness is gone."""
    def critique(value, criteria, task):
        return Critique(issues=[] if value >= 5 else [Issue("value", "too small", "major")])

    engine = LoopEngine(max_passes=4)
    result = engine.run(
        task=None,
        criteria_fn=lambda t: ["value >= 5"],
        draft_fn=lambda t, c: 1,
        critique_fn=critique,
        revise_fn=lambda o, cr, c, t: o + 2,  # repair by incrementing
    )
    assert result.output >= 5
    assert result.converged is True
    assert 1 < result.num_passes <= 4


def test_stops_at_max_passes_without_convergence():
    """A never-satisfiable critique stops at max_passes and reports not converged."""
    engine = LoopEngine(max_passes=3)
    result = engine.run(
        task=None,
        criteria_fn=lambda t: ["impossible"],
        draft_fn=lambda t, c: 0,
        critique_fn=lambda o, c, t: Critique(issues=[Issue("x", "never ok", "block")]),
        revise_fn=lambda o, cr, c, t: o,
    )
    assert result.converged is False
    assert result.num_passes == 3


def test_only_material_issues_force_revision():
    """Minor-only critiques count as passing (no material issues)."""
    crit = Critique(issues=[Issue("x", "cosmetic", "minor")])
    assert crit.passes is True
    assert crit.material_issues == []


def test_max_passes_must_be_positive():
    with pytest.raises(ValueError):
        LoopEngine(max_passes=0)


def test_transcript_records_each_pass():
    engine = LoopEngine(max_passes=4)
    result = engine.run(
        task=None,
        criteria_fn=lambda t: [],
        draft_fn=lambda t, c: 0,
        critique_fn=lambda o, c, t: Critique(issues=[] if o >= 2 else [Issue("v", "low", "major")]),
        revise_fn=lambda o, cr, c, t: o + 1,
    )
    transcript = result.transcript()
    assert [p["pass"] for p in transcript] == list(range(1, result.num_passes + 1))
