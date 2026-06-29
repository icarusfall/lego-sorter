"""Append-only JSONL store for v1.

Why JSONL rather than SQLite for v1: captures happen one-at-a-time on the Pi, often
offline, and we want crash-safe append with zero schema-migration overhead while the
schema is still moving. Each scan is one line; sessions live in their own file. When
the schema settles and we need queries/joins at scale, swap this for SQLite behind the
same interface (see docs/PROJECT_BRIEF.md §8: "SQLite or JSONL store for v1").
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from .schema import BrickScan, Session


class ScanStore:
    """One JSONL file of `BrickScan` rows + one of `Session` rows under `root`."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.scans_path = self.root / "scans.jsonl"
        self.sessions_path = self.root / "sessions.jsonl"

    # --- scans ---
    def append_scan(self, scan: BrickScan) -> None:
        with self.scans_path.open("a", encoding="utf-8") as f:
            f.write(scan.model_dump_json())
            f.write("\n")

    def read_scans(self) -> Iterator[BrickScan]:
        if not self.scans_path.exists():
            return
        with self.scans_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield BrickScan.model_validate_json(line)

    # --- sessions ---
    def append_session(self, session: Session) -> None:
        with self.sessions_path.open("a", encoding="utf-8") as f:
            f.write(session.model_dump_json())
            f.write("\n")

    def read_sessions(self) -> Iterator[Session]:
        if not self.sessions_path.exists():
            return
        with self.sessions_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield Session.model_validate_json(line)
