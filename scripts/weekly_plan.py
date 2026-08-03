"""Generate a human-readable weekly content plan from the VIRALWORKS engine.

Runs a growth cycle, then writes a markdown plan (hooks, scripts, shot beats,
captions, hashtags, best post time) that a creator can film straight from.
Used by the scheduled GitHub Actions workflow.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # run from anywhere, incl. CI

from viralworks.config import load_config  # noqa: E402
from viralworks.orchestrator import Orchestrator  # noqa: E402

PLANS_DIR = REPO_ROOT / "content_plans"


def build_plan(reels: int = 5) -> Path:
    cfg = load_config()
    orch = Orchestrator(cfg)
    result = orch.run_cycle()

    heur = orch.store.playbook_heuristics(cfg.niche)
    best_hour = heur["best_post_hour"]
    today = date.today().isoformat()

    lines: list[str] = [
        f"# Content plan — week of {today}",
        "",
        f"**Niche:** {cfg.niche}  ·  **Cycle:** {result.cycle}  ·  "
        f"**Playbook:** v{result.growth.playbook_version}",
        "",
        "## What the engine has learned so far",
        f"- Best hook style: **{heur['default_hook_style']}**",
        f"- Target length: **{heur['target_length_sec']:.0f}s**",
        f"- Best post hour: **{best_hour}:00**",
        f"- Formats that work: **{', '.join(heur['preferred_formats'])}**",
        "",
        f"_{result.growth.summary}_",
        "",
        "---",
        "",
        f"## This week's {reels} reels",
        "",
    ]

    # Re-derive the shipped pieces into readable briefs.
    top = result.board[:reels]
    ctx_cycle = result.cycle
    from viralworks.agents import CreativeAgent, ProductionAgent
    from viralworks.agents.base import AgentContext

    ctx: AgentContext = orch._context(ctx_cycle)
    creative, production = CreativeAgent(ctx), ProductionAgent(ctx)

    for i, opp in enumerate(top, start=1):
        brief = creative.run(opp).output
        spec = production.run(brief).output
        lines += [
            f"### {i}. {opp.topic}",
            "",
            f"**Hook (first 2s):** {brief.hook}",
            "",
            f"**Script:** {brief.script}",
            "",
            f"**Length:** {spec.length_sec:.0f}s  ·  **Format:** {brief.content_format}  "
            f"·  **Hook style:** {brief.hook_style}  ·  **Vertical 9:16**",
            "",
            "**Shot list:**",
            "",
        ]
        for b in spec.storyboard:
            lines.append(
                f"- `{b['t_start']:>4.1f}–{b['t_end']:<4.1f}s` {b['visual']} "
                f"— on-screen: *\"{b['on_screen_text']}\"*"
            )
        lines += [
            "",
            f"**Caption:** {spec.caption}",
            "",
            f"**Hashtags:** {' '.join(spec.hashtags)}",
            "",
            f"**Post at:** ~{best_hour}:00 local",
            "",
            "---",
            "",
        ]

    lines += [
        "## Scoreboard (simulated until real analytics are wired)",
        "",
        f"- Avg traction: **{result.avg_traction:.3f}**",
        f"- Blended ROI: **{result.analytics.blended_roi:.0f}**",
        f"- Bottleneck: {result.ops.bottleneck}",
        "",
        "> Generated automatically by the VIRALWORKS engine.",
    ]

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLANS_DIR / f"{today}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    latest = PLANS_DIR / "LATEST.md"
    latest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    path = build_plan(n)
    print(f"Wrote {path}")
