"""Configuration loading for VIRALWORKS.

Everything user-specific lives here (and in ``config.yaml`` / ``.env``) instead of
being hardcoded across the codebase. The loader is dependency-free: it will use
PyYAML if installed, otherwise it falls back to a small YAML-subset parser that
understands the structure used by ``config.yaml`` (nested maps, lists, scalars,
comments). Missing files or keys fall back to sane defaults so the system always
runs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"


# --------------------------------------------------------------------------- #
# Minimal YAML loader (no third-party dependency required)
# --------------------------------------------------------------------------- #
def _coerce_scalar(raw: str) -> Any:
    """Convert a YAML scalar string into a Python value."""
    text = raw.strip()
    if text == "" or text == "~" or text.lower() == "null":
        return None
    if (text[0] == text[-1]) and text[0] in ("'", '"') and len(text) >= 2:
        return text[1:-1]
    low = text.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _strip_comment(line: str) -> str:
    """Remove a trailing ``# comment`` while respecting quotes."""
    out, in_single, in_double = [], False, False
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
    return "".join(out)


def _minimal_yaml_load(text: str) -> Dict[str, Any]:
    """Parse the YAML subset used by config.yaml into nested dicts/lists.

    Supports: nested mappings via indentation, ``- item`` sequences, inline
    ``[a, b]`` lists, scalars, quoted strings, and ``# comments``. This is
    deliberately small; for anything richer, install PyYAML.
    """
    root: Dict[str, Any] = {}
    # stack of (indent, container) for mappings
    stack: List[tuple[int, Any]] = [(-1, root)]
    current_list_key: List[Any] = [None] * 0  # unused sentinel

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw_line = _strip_comment(lines[i]).rstrip()
        if not raw_line.strip():
            i += 1
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()

        # Pop back to the correct parent based on indentation.
        while stack and stack[-1][0] >= indent and not isinstance(stack[-1][1], list):
            stack.pop()
        parent = stack[-1][1]

        if stripped.startswith("- "):
            # sequence item belonging to the nearest list container
            value = _coerce_scalar(stripped[2:])
            if isinstance(parent, list):
                parent.append(value)
            i += 1
            continue

        if ":" not in stripped:
            i += 1
            continue

        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest == "":
            # Look ahead: is the next non-empty line a list or a nested map?
            j = i + 1
            child: Any = {}
            while j < len(lines):
                peek = _strip_comment(lines[j]).rstrip()
                if not peek.strip():
                    j += 1
                    continue
                peek_indent = len(peek) - len(peek.lstrip(" "))
                if peek_indent <= indent:
                    break
                if peek.strip().startswith("- "):
                    child = []
                break
            parent[key] = child
            stack.append((indent, child))
        elif rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            items = [_coerce_scalar(p) for p in inner.split(",")] if inner else []
            parent[key] = items
        else:
            parent[key] = _coerce_scalar(rest)
        i += 1

    return root


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return _minimal_yaml_load(text)


def _load_dotenv(path: Path) -> None:
    """Populate os.environ from a .env file (does not overwrite existing vars)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


# --------------------------------------------------------------------------- #
# Config dataclasses
# --------------------------------------------------------------------------- #
@dataclass
class LLMConfig:
    provider: str = "stub"
    model: str = "stub-model"
    api_key: str = ""


@dataclass
class VideoGenConfig:
    provider: str = "stub"
    api_key: str = ""


@dataclass
class Integrations:
    instagram_graph_api: str = ""
    tiktok_api: str = ""
    youtube_data_api: str = ""
    trend_data_source: str = ""


@dataclass
class Config:
    company_name: str = "VIRALWORKS"
    niche: str = "AI tools"
    brand_voice: str = "punchy, witty, high-energy"
    platforms: List[str] = field(
        default_factory=lambda: ["instagram_reels", "tiktok", "youtube_shorts"]
    )
    primary_goal: str = "maximize traction + monetization"
    reels_per_week_target: int = 10
    auto_publish: bool = False
    llm: LLMConfig = field(default_factory=LLMConfig)
    video_generation: VideoGenConfig = field(default_factory=VideoGenConfig)
    integrations: Integrations = field(default_factory=Integrations)
    learning_store: str = "sqlite"
    growth_cycle: str = "weekly"
    # Local paths (kept out of the yaml so they resolve relative to the repo).
    data_dir: Path = field(default_factory=lambda: REPO_ROOT / "data")
    playbooks_dir: Path = field(default_factory=lambda: REPO_ROOT / "playbooks")
    reports_dir: Path = field(default_factory=lambda: REPO_ROOT / "reports")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "viralworks.db"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.playbooks_dir, self.reports_dir):
            d.mkdir(parents=True, exist_ok=True)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_config(path: Path | str | None = None) -> Config:
    """Load Config from config.yaml + .env, with env overriding secrets."""
    _load_dotenv(REPO_ROOT / ".env")
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    raw = _load_yaml_file(path)

    llm_raw = raw.get("llm", {}) or {}
    vg_raw = raw.get("video_generation", {}) or {}
    integ_raw = raw.get("integrations", {}) or {}

    llm = LLMConfig(
        provider=str(llm_raw.get("provider") or "stub"),
        model=str(llm_raw.get("model") or "stub-model"),
        # Prefer .env for secrets; fall back to yaml if provided.
        api_key=_env("LLM_API_KEY", str(llm_raw.get("api_key") or "")),
    )
    video = VideoGenConfig(
        provider=str(vg_raw.get("provider") or "stub"),
        api_key=_env("VIDEO_API_KEY", str(vg_raw.get("api_key") or "")),
    )
    integrations = Integrations(
        instagram_graph_api=_env(
            "INSTAGRAM_GRAPH_API", str(integ_raw.get("instagram_graph_api") or "")
        ),
        tiktok_api=_env("TIKTOK_API", str(integ_raw.get("tiktok_api") or "")),
        youtube_data_api=_env(
            "YOUTUBE_DATA_API", str(integ_raw.get("youtube_data_api") or "")
        ),
        trend_data_source=_env(
            "TREND_DATA_SOURCE", str(integ_raw.get("trend_data_source") or "")
        ),
    )

    platforms = raw.get("platforms") or ["instagram_reels", "tiktok", "youtube_shorts"]

    return Config(
        company_name=str(raw.get("company_name") or "VIRALWORKS"),
        niche=str(raw.get("niche") or "AI tools"),
        brand_voice=str(raw.get("brand_voice") or "punchy, witty, high-energy"),
        platforms=list(platforms),
        primary_goal=str(raw.get("primary_goal") or "maximize traction + monetization"),
        reels_per_week_target=int(raw.get("reels_per_week_target") or 10),
        auto_publish=bool(raw.get("auto_publish") or False),
        llm=llm,
        video_generation=video,
        integrations=integrations,
        learning_store=str(raw.get("learning_store") or "sqlite"),
        growth_cycle=str(raw.get("growth_cycle") or "weekly"),
    )
