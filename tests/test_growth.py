"""Tests for the Learning Store and the Self-Growth Engine (validated learning)."""

from pathlib import Path

from viralworks.config import Config
from viralworks.contracts import PieceRecord
from viralworks.learning.growth import GrowthEngine
from viralworks.learning.store import SQLiteLearningStore
from viralworks.orchestrator import Orchestrator

from conftest import make_ctx


def _piece(i, hook, traction, holdout, niche="AI tools", fmt="listicle"):
    return PieceRecord(
        piece_id=f"p{i}", cycle=1, niche=niche, topic=f"t{i}", content_format=fmt,
        hook_style=hook, length_sec=22.0, post_hour=18, why_now="", predicted_traction=0.5,
        cost_usd=0.3, views=8000, watch_through=traction, traction_score=traction,
        roi=100.0, is_holdout=holdout,
    )


def test_growth_validates_learning_with_clear_signal():
    ctx = make_ctx()
    engine = GrowthEngine(ctx)
    pieces = []
    # 'voiceover' clearly wins; both train and holdout well represented.
    for i in range(30):
        hook = "voiceover" if i % 2 == 0 else "text"
        traction = 0.80 if hook == "voiceover" else 0.45
        holdout = (i % 3 == 0)  # ~1/3 held out, both groups present
        pieces.append(_piece(i, hook, traction, holdout))
    updates, learnings = engine._extract_learnings("AI tools", pieces)
    dims = {l.dimension: l for l in learnings}
    assert "hook_style" in dims
    assert updates["default_hook_style"] == "voiceover"
    assert dims["hook_style"].lift > 0


def test_growth_refuses_to_learn_from_noise():
    ctx = make_ctx()
    engine = GrowthEngine(ctx)
    pieces = []
    # No real signal: traction is essentially flat across hook styles.
    styles = ["text", "voiceover", "visual", "question", "stat"]
    for i in range(40):
        hook = styles[i % len(styles)]
        traction = 0.50 + (0.001 if i % 2 else -0.001)  # negligible
        pieces.append(_piece(i, hook, traction, holdout=(i % 3 == 0)))
    updates, learnings = engine._extract_learnings("AI tools", pieces)
    assert not any(l.dimension == "hook_style" for l in learnings)


def test_store_persists_across_reopen(tmp_path: Path):
    db = tmp_path / "vw.db"
    store = SQLiteLearningStore(db)
    store.add_piece(_piece(1, "voiceover", 0.8, False))
    store.save_playbook("AI tools", {"default_hook_style": "voiceover"}, [])
    store.close()

    reopened = SQLiteLearningStore(db)
    assert len(reopened.pieces(niche="AI tools")) == 1
    assert reopened.playbook_version("AI tools") == 1
    assert reopened.playbook_heuristics("AI tools")["default_hook_style"] == "voiceover"


def test_playbook_versioning_increments():
    store = make_ctx().store
    v1 = store.save_playbook("AI tools", {"default_hook_style": "text"}, [])
    v2 = store.save_playbook("AI tools", {"default_hook_style": "voiceover"}, [])
    assert (v1, v2) == (1, 2)
    assert store.playbook_heuristics("AI tools")["default_hook_style"] == "voiceover"


def test_second_cycle_uses_first_cycle_learnings(tmp_path: Path):
    """End-to-end: later cycles improve traction and the agents change behaviour."""
    cfg = Config(niche="AI tools")
    cfg.data_dir = tmp_path / "data"
    cfg.playbooks_dir = tmp_path / "playbooks"
    cfg.reports_dir = tmp_path / "reports"
    cfg.ensure_dirs()

    orch = Orchestrator(cfg)
    results = orch.run_cycles(4)

    first, last = results[0], results[-1]
    # The company got measurably better.
    assert last.avg_traction > first.avg_traction
    # It learned the (hidden) best hook and now the agents use it.
    heur = orch.store.playbook_heuristics("AI tools")
    assert heur["default_hook_style"] == "voiceover"
    assert "hook_style" in heur["validated_dims"]
    # The agents' heuristics actually changed from the cold-start default.
    assert last.heuristics_used["default_hook_style"] != first.heuristics_used["default_hook_style"]
