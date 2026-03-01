from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from flashcards_app.core.models import Card


@dataclass
class StudyStats:
    again: int = 0
    hard: int = 0
    good: int = 0
    easy: int = 0


class StudySession:
    """
    Sessão simples (sem agendamento por data/hora).
    Emula a experiência de flashcard:
    - mostra pergunta
    - revela resposta
    - usuário avalia (Again/Hard/Good/Easy)
    """
    def __init__(self, cards: list[Card], shuffle: bool = True) -> None:
        self._cards = cards[:]
        if shuffle:
            random.shuffle(self._cards)

        self._idx = 0
        self._answer_visible = False
        self.stats = StudyStats()

    def has_cards(self) -> bool:
        return len(self._cards) > 0

    def progress_text(self) -> str:
        if not self.has_cards():
            return "0/0"
        return f"{min(self._idx + 1, len(self._cards))}/{len(self._cards)}"

    def current(self) -> Optional[Card]:
        if not self.has_cards():
            return None
        if self._idx >= len(self._cards):
            return None
        return self._cards[self._idx]

    def answer_visible(self) -> bool:
        return self._answer_visible

    def toggle_answer(self) -> None:
        self._answer_visible = not self._answer_visible

    def rate_and_next(self, rating: str) -> None:
        rating = rating.lower().strip()
        if rating == "again":
            self.stats.again += 1
        elif rating == "hard":
            self.stats.hard += 1
        elif rating == "good":
            self.stats.good += 1
        elif rating == "easy":
            self.stats.easy += 1
        else:
            raise ValueError("Rating inválido.")

        self._idx += 1
        self._answer_visible = False