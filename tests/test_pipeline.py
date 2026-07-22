"""Each department handoff is testable in isolation."""

from viralworks.agents import (
    CreativeAgent,
    DiscoveryAgent,
    DistributionAgent,
    ProductionAgent,
    QAAgent,
)
from viralworks.contracts import Brief, Opportunity

from conftest import make_ctx


def _brief(ctx):
    return Brief(niche=ctx.config.niche, brand_voice=ctx.config.brand_voice, platforms=ctx.config.platforms)


def test_discovery_produces_ranked_board():
    ctx = make_ctx()
    board = DiscoveryAgent(ctx).run(_brief(ctx)).output
    assert len(board.opportunities) >= 4
    ranked = board.ranked()
    assert all(
        ranked[i].predicted_traction >= ranked[i + 1].predicted_traction
        for i in range(len(ranked) - 1)
    )
    # no dead trends survive the loop
    assert all(o.predicted_traction >= 0.35 for o in board.opportunities)


def test_creative_loop_makes_hook_strong_and_trims_runtime():
    ctx = make_ctx()
    board = DiscoveryAgent(ctx).run(_brief(ctx)).output
    result = CreativeAgent(ctx).run(board.top())
    brief = result.output
    # loop converged: hook is punchy (<=12 words) and runtime within target+2
    target = ctx.heuristics(ctx.config.niche)["target_length_sec"]
    assert len(brief.hook.split()) <= 12
    assert brief.length_sec <= target + 2
    assert brief.cta and len(brief.hashtags) >= 3


def test_production_emits_render_ready_spec():
    ctx = make_ctx()
    board = DiscoveryAgent(ctx).run(_brief(ctx)).output
    brief = CreativeAgent(ctx).run(board.top()).output
    spec = ProductionAgent(ctx).run(brief).output
    assert spec.aspect_ratio == "9:16"
    assert abs(spec.length_sec - brief.length_sec) < 0.5
    assert len(spec.render_prompts) == len(brief.shot_list)
    assert spec.captions_srt.strip()
    assert spec.caption == brief.caption  # no spec drift


def test_qa_approves_clean_spec_but_requires_human_review():
    ctx = make_ctx()
    board = DiscoveryAgent(ctx).run(_brief(ctx)).output
    brief = CreativeAgent(ctx).run(board.top()).output
    spec = ProductionAgent(ctx).run(brief).output
    report = QAAgent(ctx).run(spec).output
    assert report.approved is True
    assert report.requires_human_review is True


def test_qa_blocks_banned_hashtag_and_misleading_claim():
    ctx = make_ctx()
    board = DiscoveryAgent(ctx).run(_brief(ctx)).output
    brief = CreativeAgent(ctx).run(board.top()).output
    spec = ProductionAgent(ctx).run(brief).output
    spec.hashtags = spec.hashtags + ["#followforfollow"]
    spec.caption = "This is guaranteed to make you rich overnight"
    report = QAAgent(ctx).run(spec).output
    assert report.approved is False
    assert any("hashtag" in b.lower() for b in report.blocks)
    assert any("claim" in b.lower() for b in report.blocks)


def test_distribution_schedules_all_platforms_and_defaults_to_human_review():
    ctx = make_ctx()
    board = DiscoveryAgent(ctx).run(_brief(ctx)).output
    brief = CreativeAgent(ctx).run(board.top()).output
    spec = ProductionAgent(ctx).run(brief).output
    result = DistributionAgent(ctx).run(spec).output
    assert set(result.platform_posts.keys()) == set(ctx.config.platforms)
    assert result.auto_published is False
    assert all(
        p["status"] == "queued_for_human_review" for p in result.platform_posts.values()
    )
    # all platforms scheduled at the same hour (consistent cross-posting)
    hours = {p["scheduled_hour"] for p in result.platform_posts.values()}
    assert len(hours) == 1
