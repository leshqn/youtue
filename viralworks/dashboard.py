"""Observability: a CLI report and a self-contained HTML page.

Shows the Opportunity Board, the finished reel spec, loop-engineering transcripts,
the ROI leaderboard, the Growth Report, the Ops bottleneck, and the cross-cycle
improvement that proves the company is learning.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import List

from .orchestrator import CycleResult

_BAR = "═" * 74


def _h(title: str) -> str:
    return f"\n{_BAR}\n  {title}\n{_BAR}"


def render_cli(results: List[CycleResult]) -> str:
    if not results:
        return "No cycles run."
    first, last = results[0], results[-1]
    cfg_niche = last.niche
    out: List[str] = []

    out.append(_h(f"VIRALWORKS — {cfg_niche} — {len(results)} cycle(s)"))

    # --- Finished reel spec (the deliverable) ------------------------------ #
    s = last.sample
    if s:
        spec, cre = s.spec, s.creative
        out.append(_h("FINISHED REEL SPEC (render-ready)"))
        out.append(f"  Topic      : {spec.topic}")
        out.append(f"  Hook       : {cre.hook}  [{cre.hook_style}]")
        out.append(f"  Format     : {cre.content_format}   Length: {spec.length_sec:.0f}s   AR: {spec.aspect_ratio}")
        out.append(f"  Audio      : {spec.audio_track}")
        out.append(f"  Caption    : {spec.caption}")
        out.append(f"  Hashtags   : {' '.join(spec.hashtags)}")
        out.append(f"  Render     : {'LIVE ' + str(spec.render_url) if spec.render_url else 'spec_only (no provider wired)'}  est_cost=${spec.est_cost_usd}")
        out.append("  Storyboard :")
        for b in spec.storyboard:
            out.append(
                f"    {b['t_start']:>4.1f}-{b['t_end']:<4.1f}s | {b['visual']} "
                f"| text:'{b['on_screen_text']}'"
            )
        out.append("  Captions (SRT):")
        for line in spec.captions_srt.splitlines()[:8]:
            out.append(f"    {line}")

        # --- Loop engineering transcripts --------------------------------- #
        out.append(_h("LOOP ENGINEERING — passes per department (criteria->critique->revise)"))
        for dept, transcript in s.loop_transcripts.items():
            passes = len(transcript)
            final = transcript[-1]["material_issues"] if transcript else 0
            verdict = "converged" if final == 0 else f"stopped ({final} issues left)"
            out.append(f"  {dept:<16} {passes} pass(es) -> {verdict}")
            for t in transcript:
                out.append(f"      pass {t['pass']}: {t['critique']}")

        # --- QA gate ------------------------------------------------------ #
        out.append(_h("BRAND SAFETY / QA GATE (human-in-the-loop)"))
        out.append(f"  Approved         : {s.qa.approved}")
        out.append(f"  Requires review  : {s.qa.requires_human_review}")
        out.append(f"  Risk flags       : {s.qa.risk_flags or ['none']}")
        out.append(f"  Blocks           : {s.qa.blocks or ['none']}")
        auto = bool(s.publish and s.publish.auto_published)
        out.append(f"  Auto-publish     : {'ON' if auto else 'OFF -> queued for human review'}")

    # --- Opportunity Board ------------------------------------------------- #
    out.append(_h(f"OPPORTUNITY BOARD (cycle {last.cycle}) — ranked bets"))
    out.append(f"  {'predicted':>9}  {'hook':<10} {'format':<14} topic")
    for o in last.board[:6]:
        out.append(
            f"  {o.predicted_traction:>9.2f}  {o.suggested_hook_style:<10} "
            f"{o.content_format:<14} {o.topic}"
        )
    if last.board:
        out.append(f"    why now (top): {last.board[0].why_now}")

    # --- ROI leaderboard --------------------------------------------------- #
    a = last.analytics
    out.append(_h(f"ROI LEADERBOARD (cycle {last.cycle}) — no vanity metrics"))
    out.append(f"  avg traction={a.avg_traction:.3f}  blended ROI={a.blended_roi:.2f}  "
               f"views={a.total_views:,}  cost=${a.total_cost_usd:.2f}")
    out.append(f"  {'traction':>8} {'roi':>7} {'views':>8}  topic")
    for row in a.leaderboard[:5]:
        out.append(
            f"  {row.get('traction', 0):>8.2f} {row.get('roi', 0):>7.1f} "
            f"{row.get('views', 0):>8,}  {row.get('topic', '')}"
        )
    if a.traction_by_hook:
        out.append(f"  traction by hook : {json.dumps(a.traction_by_hook)}")
    if a.roi_by_format:
        out.append(f"  roi by format    : {json.dumps(a.roi_by_format)}")
    out.append(f"  winners          : {a.winners}")
    out.append(f"  losers           : {a.losers}")

    # --- Growth Report ----------------------------------------------------- #
    g = last.growth
    out.append(_h(f"GROWTH REPORT (cycle {g.cycle}) — playbook v{g.playbook_version}"))
    out.append(f"  {g.summary}")
    out.append(f"  validated holdout lift: +{g.validated_lift:.3f}")
    if g.learnings:
        out.append("  Learnings adopted:")
        for l in g.learnings:
            out.append(f"    - [{l.dimension}] {l.recommendation}  ({l.evidence}; conf {l.confidence:.2f})")
    else:
        out.append("  Learnings adopted: none validated this cycle.")
    out.append(f"  Roster changes (HR): {g.roster_changes}")
    out.append(f"  Strategy objective : {g.strategy_objective}")

    # --- Ops --------------------------------------------------------------- #
    op = last.ops
    out.append(_h("OPS — throughput, cost & bottleneck"))
    out.append(f"  reels={op.reels_produced}/{op.target}  cost/reel=${op.cost_per_reel}  "
               f"total=${op.total_cost_usd}  model_calls={op.model_calls}")
    out.append(f"  bottleneck : {op.bottleneck}")
    out.append(f"  10x plan   : {op.scale_plan[0] if op.scale_plan else 'n/a'}")

    # --- Cross-cycle improvement (the proof of learning) ------------------- #
    if len(results) > 1:
        out.append(_h("SELF-GROWTH — did it get better?"))
        out.append(f"  avg traction:  cycle {first.cycle} = {first.avg_traction:.3f}"
                   f"  ->  cycle {last.cycle} = {last.avg_traction:.3f}"
                   f"  ({'+' if last.avg_traction >= first.avg_traction else ''}"
                   f"{(last.avg_traction - first.avg_traction):.3f})")
        out.append(f"  blended ROI :  cycle {first.cycle} = {first.analytics.blended_roi:.2f}"
                   f"  ->  cycle {last.cycle} = {last.analytics.blended_roi:.2f}")
        out.append(f"  playbook    :  v1  ->  v{last.growth.playbook_version} "
                   f"(learnings compounded into the agents)")
        # What the agents actually DO differently now (heuristics evolution).
        out.append("  heuristics the agents use (what changed):")
        for key in ("default_hook_style", "target_length_sec", "best_post_hour", "preferred_formats"):
            a0 = first.heuristics_used.get(key)
            a1 = last.heuristics_used.get(key)
            marker = "  <-- changed by learning" if a0 != a1 else ""
            out.append(f"    {key:<20} {a0}  ->  {a1}{marker}")

    # --- Spend ------------------------------------------------------------- #
    out.append(_h("SPEND"))
    out.append(f"  LLM calls={last.llm_calls}  LLM spend=${last.llm_cost_usd:.4f} "
               f"({'LIVE provider' if last.llm_cost_usd > 0 else 'stub — $0, wire a key for real spend'})")

    return "\n".join(out)


def write_html(results: List[CycleResult], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = html.escape(render_cli(results))
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>VIRALWORKS Dashboard</title>
<style>
  body {{ background:#0b0e14; color:#d6deeb; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; margin:0; padding:2rem; }}
  h1 {{ color:#7fdbca; }}
  pre {{ white-space:pre-wrap; line-height:1.4; font-size:13px; }}
  .card {{ background:#111725; border:1px solid #1f2a3d; border-radius:10px; padding:1.2rem 1.6rem; max-width:1000px; }}
</style></head>
<body>
  <h1>VIRALWORKS — self-growing AI content company</h1>
  <div class="card"><pre>{body}</pre></div>
</body></html>
"""
    path.write_text(page, encoding="utf-8")
    return path
