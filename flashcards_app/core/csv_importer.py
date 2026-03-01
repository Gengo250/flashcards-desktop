from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from flashcards_app.services.errors import CsvFormatError


@dataclass(frozen=True)
class CsvCardRow:
    number: Optional[int]
    question: str
    answer: str


def _normalize(s: str) -> str:
    return s.strip().lower()


def read_cards_from_csv(csv_path: Path) -> list[CsvCardRow]:
    if not csv_path.exists():
        raise CsvFormatError(f"Arquivo não encontrado: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise CsvFormatError("CSV sem cabeçalhos.")

        headers = [_normalize(h) for h in reader.fieldnames]

        # Aceita sinônimos comuns, mas recomenda o padrão: numero, pergunta, resposta
        aliases = {
            "numero": {"numero", "n", "id", "num", "number"},
            "pergunta": {"pergunta", "questao", "question", "q", "frente", "front"},
            "resposta": {"resposta", "answer", "a", "verso", "back"},
        }

        def pick(required_key: str) -> str:
            for h in headers:
                if h in aliases[required_key]:
                    return h
            raise CsvFormatError(
                f"Cabeçalho obrigatório ausente. Precisa de: {sorted(list(aliases[required_key]))}"
            )

        h_num = pick("numero")
        h_q = pick("pergunta")
        h_a = pick("resposta")

        rows: list[CsvCardRow] = []
        line_no = 1  # header line is 1
        for row in reader:
            line_no += 1
            q = (row.get(h_q) or "").strip()
            a = (row.get(h_a) or "").strip()
            raw_num = (row.get(h_num) or "").strip()

            if not q or not a:
                raise CsvFormatError(f"Linha {line_no}: pergunta/resposta vazia.")

            number: Optional[int] = None
            if raw_num:
                try:
                    number = int(raw_num)
                except ValueError:
                    raise CsvFormatError(f"Linha {line_no}: 'numero' precisa ser inteiro, veio: {raw_num!r}")

            rows.append(CsvCardRow(number=number, question=q, answer=a))

        if not rows:
            raise CsvFormatError("CSV não contém cards.")
        return rows