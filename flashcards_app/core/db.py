from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class Database:
    path: Path

    @staticmethod
    def default() -> "Database":
        base_dir = Path.home() / ".flashcards_app"
        base_dir.mkdir(parents=True, exist_ok=True)
        return Database(path=base_dir / "flashcards.sqlite3")

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize_schema(self) -> None:
        schema = [
            """
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                number INTEGER,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_cards_deck_id ON cards(deck_id);",
            "CREATE INDEX IF NOT EXISTS idx_cards_due_number ON cards(deck_id, number);",
        ]
        with self.connect() as conn:
            for stmt in schema:
                conn.execute(stmt)
            conn.commit()