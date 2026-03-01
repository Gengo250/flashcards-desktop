from __future__ import annotations

from typing import Iterable, Optional

from flashcards_app.core.db import Database
from flashcards_app.core.models import Card


class CardRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_by_deck(self, deck_id: int) -> list[Card]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, deck_id, number, question, answer FROM cards WHERE deck_id = ? ORDER BY COALESCE(number, 999999), id;",
                (deck_id,),
            ).fetchall()
            return [
                Card(
                    id=int(r["id"]),
                    deck_id=int(r["deck_id"]),
                    number=(int(r["number"]) if r["number"] is not None else None),
                    question=str(r["question"]),
                    answer=str(r["answer"]),
                )
                for r in rows
            ]

    def insert_many(self, deck_id: int, cards: Iterable[tuple[Optional[int], str, str]]) -> int:
        items = [(deck_id, n, q, a) for (n, q, a) in cards]
        with self.db.connect() as conn:
            conn.executemany(
                "INSERT INTO cards(deck_id, number, question, answer) VALUES (?, ?, ?, ?);",
                items,
            )
            conn.commit()
            return len(items)

    def delete_all_in_deck(self, deck_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM cards WHERE deck_id = ?;", (deck_id,))
            conn.commit()