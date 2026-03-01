from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Deck:
    id: int
    name: str


@dataclass(frozen=True)
class Card:
    id: int
    deck_id: int
    number: Optional[int]
    question: str
    answer: str