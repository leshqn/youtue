# VIRALWORKS — a self-growing AI content company

VIRALWORKS is an autonomous, assembly-line company of specialized AI
"department" agents that **discover trends → refine ideas into scripts and shot
plans → produce a render-ready reel spec → gate it for brand safety → publish it
→ measure real performance → and rewrite their own playbooks so next week's
output beats this week's.**

It runs **end-to-end today with zero API keys** (everything external is stubbed
behind clean seams), and every external dependency has a documented slot to drop
a live provider in.

```bash
make run          # 4 cycles on stubs -> prints a real reel spec + Growth Report
```

North star: **traction that converts to money** — watch-through, shares, saves,
follows-per-view, and downstream ROI. No vanity metrics.

---

## The two loops (the core operating principle)

1. **The runtime loop (every agent, every task).** Before any department hands
   work downstream it runs a `criteria → draft → critique → revise → decide`
   cycle on its own output, stopping when the critique finds nothing material or
   after ~4 passes. This is implemented **once** in
   [`loop_engine.py`](viralworks/loop_engine.py) and imported by every agent, so
   the discipline is enforced *structurally*, not left to chance. You can watch
   it work in the dashboard's **LOOP ENGINEERING** section (e.g. Studio takes a
   second pass to punch up a weak hook and trim runtime).

2. **The self-growth loop (the company).** Analytics measures every shipped
   piece; the Growth Engine correlates features with traction, keeps only the
   learnings that survive a **held-out A/B validation**, rewrites the per-niche
   playbook, and HR + Strategy act on the roster and objectives. The company
   gets **measurably better every cycle** (see the dashboard's **SELF-GROWTH**
   section).

---

## Org chart (9 departments, one `Agent` interface)

| # | Department | Agent | KPIs it's judged on |
|---|-----------|-------|---------------------|
| — | CEO/COO (Orchestrator) | [`orchestrator.py`](viralworks/orchestrator.py) | pipeline throughput, ships only what QA approved |
| 1 | R&D — Trend & Content Discovery | [`discovery.py`](viralworks/agents/discovery.py) | predicted-vs-actual traction, niche fit |
| 2 | Studio — Creative & Refinement | [`creative.py`](viralworks/agents/creative.py) | hook strength, watch-through, runtime discipline |
| 3 | Factory — Production | [`production.py`](viralworks/agents/production.py) | spec fidelity, captions, correct format/length |
| 4 | Quality/Legal — Brand Safety & QA | [`qa.py`](viralworks/agents/qa.py) | risk catch rate, false-block rate |
| 5 | Growth — Distribution & Publishing | [`distribution.py`](viralworks/agents/distribution.py) | cadence, on-time scheduling, per-platform fit |
| 6 | The Numbers — ROI, Finance & Analytics | [`analytics.py`](viralworks/agents/analytics.py) | ROI accuracy, north-star coverage |
| 7 | Ops — Scalability & Operations | [`ops.py`](viralworks/agents/ops.py) | cost per reel, throughput vs target |
| 8 | People Ops — HR for Agents | [`hr.py`](viralworks/agents/hr.py) | roster ROI, specialist hit rate |
| 9 | Boardroom — Strategy | [`strategy.py`](viralworks/agents/strategy.py) | objective clarity, OKR measurability |

Each agent declares its `kpis` and `failure_modes`; the critique step actively
checks those failure modes.

## The assembly line

```
Discovery → Creative → Production → QA → Distribution → Analytics
        └────────── Self-Growth Engine (Analytics + HR + Strategy) ──────────┘
                              ↺ rewrites the playbook every cycle
```

Every arrow is a **typed contract** (see [`contracts.py`](viralworks/contracts.py):
`Brief`, `Opportunity`, `CreativeBrief`, `ReelSpec`, `QAReport`,
`PublishResult`, `Metrics`, `PieceRecord`, `GrowthReport`), so each department is
**testable in isolation** (see [`tests/test_pipeline.py`](tests/test_pipeline.py)).

---

## The Self-Growth Engine (how "always growing" is real, not vibes)

[`learning/growth.py`](viralworks/learning/growth.py) + a persistent Learning
Store ([`learning/store.py`](viralworks/learning/store.py), SQLite by default,
interface swappable).

Each Growth Cycle:

1. **Correlates** features (hook style, format, length, post hour) with traction
   across every piece ever shipped in the niche.
2. **Validates** each candidate learning with a **two-sample z-test on a held-out
   split** — a candidate must beat the field on data it was *not* selected on,
   by a minimum lift *and* a minimum z-score. Weak/noisy dimensions are
   **refused** rather than "learned." This is the guard against critique theatre.
3. **Rewrites** the per-niche playbook heuristics (versioned in the DB **and** as
   markdown under [`playbooks/`](playbooks) — history is never overwritten).
4. **Explore/exploit with confirmation bias protection:** a dimension is
   explored *uniformly* until it has a validated learning, then exploited (with a
   small exploration epsilon). This keeps the sample unbiased so the company
   never "learns" from data its own policy skewed.
5. **HR** tunes/spawns/retires agents (e.g. spins up a "Hook Specialist" when a
   hook style clearly separates winners); **Strategy** resets the objective/OKRs.
6. Logs a short **Growth Report** (what changed, the evidence, expected impact).

**Proof it works** (default `make run`, niche = *AI tools*):

```
avg traction:  cycle 1 = 0.55  ->  cycle 4 = 0.69   (+0.14)
default_hook_style   text  ->  voiceover   <-- changed by learning
preferred_formats    [listicle,…]  ->  [reaction,…] <-- changed by learning
```

The stub analytics encodes a *hidden* per-niche "world model" (best hook, length,
hour, format) that the company **cannot see** — it must discover it from
outcomes. The learned playbook converges to that hidden optimum on the strong
signals and honestly declines to over-claim on the noisy ones.

---

## Running it

```bash
make run              # clean 4-cycle demo (wipes generated state first)
make demo             # 6-cycle showcase
make persist          # 1 cycle WITHOUT wiping — proves memory survives runs
make test             # pytest
make clean            # remove generated data/reports/playbooks

# or directly:
python -m viralworks --cycles 4 --fresh
python -m viralworks --niche "fitness" --cycles 5
python -m viralworks --cycles 1            # persisted (accumulates learnings)
```

No API keys required. Outputs a real reel spec, a Growth Report, and an HTML
dashboard at `reports/dashboard.html`.

**Requirements:** Python 3.10+. The core has **no third-party dependencies**
(stdlib only). `pytest` is needed only for the tests; PyYAML and `anthropic` are
optional (see below).

---

## Stubbed vs. live — how to go live

Everything external is a seam with a working stub. To go live, edit
[`config.yaml`](config.yaml) + [`.env`](.env.example) and implement the marked
slot. Nothing else in the pipeline changes.

| Integration | Stub (default) | Go live |
|---|---|---|
| **LLM** ([`llm/`](viralworks/llm)) | deterministic, $0, templates are authoritative | set `llm.provider: anthropic` + `llm.model` in `config.yaml`, put `LLM_API_KEY` in `.env`, `pip install anthropic`. Agents then use real prose via [`_maybe_llm`](viralworks/agents/base.py); cost is logged automatically. |
| **Video gen** ([`integrations/video.py`](viralworks/integrations/video.py)) | ships a render-ready spec + storyboard (no file) | implement `LiveVideoGenerator.render()` against a text-to-video API; set `video_generation.provider` + `VIDEO_API_KEY`. |
| **Publishing** ([`integrations/publishing.py`](viralworks/integrations/publishing.py)) | records intent, never posts | implement `LiveInstagram/TikTok/YouTubePublisher.publish()`; set the matching key in `integrations:`. |
| **Trends** ([`integrations/trends.py`](viralworks/integrations/trends.py)) | deterministic per (niche, cycle) | implement `LiveTrendSource.fetch()` (respect ToS + rate limits); set `trend_data_source`. |
| **Analytics** ([`integrations/analytics_api.py`](viralworks/integrations/analytics_api.py)) | hidden world model → realistic metrics | implement `LiveMetricsSource.metrics_for()` against platform Insights. |

Any integration whose key is left blank stays on its stub, so you can go live
one piece at a time.

---

## Guardrails (non-negotiable, on by default)

- **Human-in-the-loop at QA**: `requires_human_review` is always `True`.
- **`auto_publish: false`** by default — posts are `queued_for_human_review`
  until you explicitly flip the flag.
- **QA blocks** ToS-violating hashtags, misleading/absolute claims (in caption
  *and* voiceover), and flags **music-licensing** risk before publish.
- **The CEO ships nothing QA blocked.**
- **All spend is logged** through the single `ModelClient`; the stub is priced at
  $0 so the spend log is honest.
- Built for real traction, **not** spam, fake engagement, or bot farms.

---

## Configuration

Edit [`config.yaml`](config.yaml) (secrets go in `.env`, see
[`.env.example`](.env.example)):

```yaml
company_name: "VIRALWORKS"
niche: "AI tools"
brand_voice: "punchy, witty, high-energy"
platforms: ["instagram_reels", "tiktok", "youtube_shorts"]
reels_per_week_target: 10
auto_publish: false          # guardrail
llm: { provider: "stub", model: "stub-model" }
video_generation: { provider: "stub" }
learning_store: "sqlite"
growth_cycle: "weekly"
```

---

## Repo layout

```
viralworks/
  loop_engine.py      # the shared runtime loop (criteria->draft->critique->revise->decide)
  contracts.py        # typed handoff objects (dataclasses)
  orchestrator.py     # CEO/COO: runs the assembly line + growth cycle
  config.py           # config.yaml + .env loader (stdlib-only YAML subset)
  dashboard.py        # CLI report + self-contained HTML page
  agents/             # the 9 departments, each behind the Agent interface
  llm/                # one ModelClient, swappable providers, cost logging
  learning/           # LearningStore (SQLite) + the Self-Growth Engine
  integrations/       # trends / video / publishing / analytics seams
tests/                # loop engine, contracts, pipeline handoffs, growth cycle
playbooks/            # versioned, learned playbooks (generated)
data/ reports/        # SQLite store + HTML dashboard (generated)
```

---

## Build phases (all complete)

- **Phase 1 — skeleton that runs:** Agent base, loop engine, orchestrator, typed
  contracts, all 9 departments; one brief flows end-to-end on mocks. ✅
- **Phase 2 — real brains:** LLM client wired via a single seam; Discovery,
  Creative, Production produce genuine briefs/specs with the loop engaged. ✅
- **Phase 3 — scoreboard & memory:** Analytics + Learning Store + Growth Cycle;
  it improves itself on measured metrics. ✅
- **Phase 4 — go-live seams:** real integrations behind flags, holdout A/B
  validation, HTML dashboard, guardrails hardened. ✅
- **Phase 5 — scale:** Ops batching/parallelism/cost plan + budget guard; HR
  spawns specialists. ✅ (throughput reports the next bottleneck each cycle)

## Definition of Done

- ✅ One command runs a full cycle end-to-end on stubs and outputs a real reel
  spec + Growth Report.
- ✅ All 9 departments exist with clear KPIs and the runtime loop engaged.
- ✅ The Learning Store persists; a later cycle demonstrably uses earlier
  learnings to change what the agents do (see `test_second_cycle_uses_first_cycle_learnings`).
- ✅ README explains architecture, how to run, and exactly how to wire live APIs.
- ✅ Tests pass (`make test`).
