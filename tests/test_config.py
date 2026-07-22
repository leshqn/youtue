"""Tests for the dependency-free config loader (minimal YAML subset)."""

from viralworks.config import _minimal_yaml_load, load_config


def test_minimal_yaml_parses_nested_and_lists():
    text = """
company_name: "VIRALWORKS"
reels_per_week_target: 10
auto_publish: false
platforms: ["instagram_reels", "tiktok"]
llm:
  provider: "stub"
  model: "stub-model"
integrations:
  tiktok_api: ""
"""
    data = _minimal_yaml_load(text)
    assert data["company_name"] == "VIRALWORKS"
    assert data["reels_per_week_target"] == 10
    assert data["auto_publish"] is False
    assert data["platforms"] == ["instagram_reels", "tiktok"]
    assert data["llm"]["provider"] == "stub"
    assert data["integrations"]["tiktok_api"] == ""


def test_minimal_yaml_handles_dash_lists():
    text = """
platforms:
  - instagram_reels
  - tiktok
  - youtube_shorts
"""
    data = _minimal_yaml_load(text)
    assert data["platforms"] == ["instagram_reels", "tiktok", "youtube_shorts"]


def test_load_config_reads_repo_config():
    cfg = load_config()
    assert cfg.company_name == "VIRALWORKS"
    assert "instagram_reels" in cfg.platforms
    assert cfg.auto_publish is False  # guardrail default
    assert cfg.db_path.name == "viralworks.db"
