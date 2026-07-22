"""The Learning Store — the company's persistent memory.

Records every shipped piece, its real (mock) performance, the active per-niche
*playbook* heuristics that agents read, and every Growth Report. The interface
is deliberately small and swappable (``LearningStore``); the default backing is
SQLite, and an in-memory implementation is provided for tests.

Playbook heuristics are the mechanism by which learning changes behaviour: the
Growth Engine writes new heuristics here, and Discovery/Creative read them on the
next cycle. History is never silently overwritten — every playbook write is a new
version.
"""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..contracts import GrowthReport, Learning, PieceRecord

# The starting heuristics an agent gets before the company has learned anything.
DEFAULT_HEURISTICS: Dict[str, Any] = {
    "default_hook_style": "text",
    "target_length_sec": 25.0,
    "best_post_hour": 18,
    "preferred_formats": ["listicle", "tutorial", "transformation"],
    # Dimensions with a holdout-validated learning. Until a dimension is listed
    # here the agents keep exploring it uniformly, so the sample stays unbiased
    # by the policy (guards against confirmation-bias "learning").
    "validated_dims": [],
    "notes": ["No learnings yet — using cold-start defaults."],
}


class LearningStore(ABC):
    """Swappable persistence interface."""

    @abstractmethod
    def next_cycle(self) -> int: ...

    @abstractmethod
    def add_piece(self, record: PieceRecord) -> None: ...

    @abstractmethod
    def pieces(
        self, niche: Optional[str] = None, cycle: Optional[int] = None
    ) -> List[PieceRecord]: ...

    @abstractmethod
    def save_playbook(
        self, niche: str, heuristics: Dict[str, Any], learnings: List[Learning]
    ) -> int:
        """Persist a new playbook version; returns the new version number."""

    @abstractmethod
    def playbook_heuristics(self, niche: str) -> Dict[str, Any]: ...

    @abstractmethod
    def playbook_version(self, niche: str) -> int: ...

    @abstractmethod
    def save_growth_report(self, report: GrowthReport) -> None: ...

    @abstractmethod
    def growth_reports(self) -> List[Dict[str, Any]]: ...


class SQLiteLearningStore(LearningStore):
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS pieces (
                piece_id TEXT PRIMARY KEY,
                cycle INTEGER,
                niche TEXT,
                topic TEXT,
                content_format TEXT,
                hook_style TEXT,
                length_sec REAL,
                post_hour INTEGER,
                why_now TEXT,
                predicted_traction REAL,
                cost_usd REAL,
                views INTEGER,
                watch_through REAL,
                traction_score REAL,
                roi REAL,
                is_holdout INTEGER,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS playbooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                niche TEXT,
                version INTEGER,
                heuristics_json TEXT,
                learnings_json TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS growth_reports (
                cycle INTEGER PRIMARY KEY,
                report_json TEXT,
                created_at REAL
            );
            """
        )
        self._conn.commit()

    # --- cycles ------------------------------------------------------------ #
    def next_cycle(self) -> int:
        cur = self._conn.execute("SELECT MAX(cycle) AS c FROM pieces")
        row = cur.fetchone()
        return (row["c"] or 0) + 1

    # --- pieces ------------------------------------------------------------ #
    def add_piece(self, record: PieceRecord) -> None:
        row = record.to_row()
        row["is_holdout"] = int(row["is_holdout"])
        cols = ",".join(row.keys())
        placeholders = ",".join(["?"] * len(row))
        self._conn.execute(
            f"INSERT OR REPLACE INTO pieces ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        self._conn.commit()

    def pieces(
        self, niche: Optional[str] = None, cycle: Optional[int] = None
    ) -> List[PieceRecord]:
        q = "SELECT * FROM pieces WHERE 1=1"
        args: List[Any] = []
        if niche is not None:
            q += " AND niche = ?"
            args.append(niche)
        if cycle is not None:
            q += " AND cycle = ?"
            args.append(cycle)
        q += " ORDER BY created_at ASC"
        rows = self._conn.execute(q, args).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["is_holdout"] = bool(d["is_holdout"])
            out.append(PieceRecord(**d))
        return out

    # --- playbooks --------------------------------------------------------- #
    def playbook_version(self, niche: str) -> int:
        cur = self._conn.execute(
            "SELECT MAX(version) AS v FROM playbooks WHERE niche = ?", (niche,)
        )
        row = cur.fetchone()
        return row["v"] or 0

    def save_playbook(
        self, niche: str, heuristics: Dict[str, Any], learnings: List[Learning]
    ) -> int:
        version = self.playbook_version(niche) + 1
        import time

        self._conn.execute(
            "INSERT INTO playbooks (niche, version, heuristics_json, learnings_json, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                niche,
                version,
                json.dumps(heuristics),
                json.dumps([asdict(l) for l in learnings]),
                time.time(),
            ),
        )
        self._conn.commit()
        return version

    def playbook_heuristics(self, niche: str) -> Dict[str, Any]:
        cur = self._conn.execute(
            "SELECT heuristics_json FROM playbooks WHERE niche = ?"
            " ORDER BY version DESC LIMIT 1",
            (niche,),
        )
        row = cur.fetchone()
        if not row:
            return dict(DEFAULT_HEURISTICS)
        merged = dict(DEFAULT_HEURISTICS)
        merged.update(json.loads(row["heuristics_json"]))
        return merged

    # --- growth reports ---------------------------------------------------- #
    def save_growth_report(self, report: GrowthReport) -> None:
        import time

        payload = asdict(report)
        self._conn.execute(
            "INSERT OR REPLACE INTO growth_reports (cycle, report_json, created_at)"
            " VALUES (?, ?, ?)",
            (report.cycle, json.dumps(payload), time.time()),
        )
        self._conn.commit()

    def growth_reports(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT report_json FROM growth_reports ORDER BY cycle ASC"
        ).fetchall()
        return [json.loads(r["report_json"]) for r in rows]

    def close(self) -> None:
        self._conn.close()


class InMemoryLearningStore(SQLiteLearningStore):
    """SQLite in ``:memory:`` — same behaviour, nothing persisted. For tests."""

    def __init__(self) -> None:
        # Bypass parent __init__'s path handling.
        self.db_path = ":memory:"
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()


def build_store(kind: str, db_path: Path | str) -> LearningStore:
    kind = (kind or "sqlite").lower()
    if kind in ("sqlite", "", "default"):
        return SQLiteLearningStore(db_path)
    if kind == "memory":
        return InMemoryLearningStore()
    # Unknown -> sqlite (documented, never crashes).
    return SQLiteLearningStore(db_path)
