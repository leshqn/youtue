"""Unit tests for the typed contracts and their derived metrics."""

from viralworks.contracts import Metrics, Opportunity, OpportunityBoard


def test_metrics_derived_properties():
    m = Metrics(
        spec_id="s", views=10000, watch_through=0.6, shares=200, saves=300,
        comments=100, follows=80, ctr=0.05, cost_usd=0.5,
    )
    assert m.follows_per_view == 80 / 10000
    assert abs(m.engagement_rate - (600 / 10000)) < 1e-9
    assert 0.0 <= m.traction_score <= 1.0
    assert m.roi > 0  # views * traction / cost


def test_metrics_zero_views_is_safe():
    m = Metrics("s", 0, 0.0, 0, 0, 0, 0, 0.0, 0.0)
    assert m.follows_per_view == 0.0
    assert m.engagement_rate == 0.0
    assert m.roi == 0.0


def test_predicted_traction_is_clamped():
    o = Opportunity(
        topic="t", niche="n", content_format="listicle", suggested_hook_style="text",
        trending_sound="x", hashtags=[], why_now="", predicted_traction=1.9,
    )
    assert o.predicted_traction == 1.0
    o2 = Opportunity(
        topic="t", niche="n", content_format="listicle", suggested_hook_style="text",
        trending_sound="x", hashtags=[], why_now="", predicted_traction=-0.5,
    )
    assert o2.predicted_traction == 0.0


def test_opportunity_board_ranking():
    def opp(score):
        return Opportunity("t", "n", "listicle", "text", "s", [], "", score)

    board = OpportunityBoard(opportunities=[opp(0.2), opp(0.9), opp(0.5)])
    ranked = board.ranked()
    assert [round(o.predicted_traction, 1) for o in ranked] == [0.9, 0.5, 0.2]
    assert board.top().predicted_traction == 0.9
