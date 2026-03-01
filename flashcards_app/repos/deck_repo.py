from __future__ import annotations

from typing import Optional

from flashcards_app.core.db import Database
from flashcards_app.core.models import Deck


class DeckRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_all(self) -> list[Deck]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT id, name FROM decks ORDER BY name ASC;").fetchall()
            return [Deck(id=int(r["id"]), name=str(r["name"])) for r in rows]

    def create(self, name: str) -> Deck:
        name = name.strip()
        if not name:
            raise ValueError("Nome da pasta/deck não pode ser vazio.")
        with self.db.connect() as conn:
            cur = conn.execute("INSERT INTO decks(name) VALUES (?);", (name,))
            conn.commit()
            return Deck(id=int(cur.lastrowid), name=name)

    def delete(self, deck_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM decks WHERE id = ?;", (deck_id,))
            conn.commit()

    def get_by_name(self, name: str) -> Optional[Deck]:
        with self.db.connect() as conn:
            row = conn.execute("SELECT id, name FROM decks WHERE name = ?;", (name.strip(),)).fetchone()
            if not row:
                return None
            return Deck(id=int(row["id"]), name=str(row["name"]))