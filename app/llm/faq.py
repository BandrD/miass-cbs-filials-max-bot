from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FaqEntry:
    id: str
    question: str
    answer: str
    keywords: list[str]


@dataclass
class FaqHit:
    entry: FaqEntry
    score: float


HELP_TEXT = (
    "**Бот ЦБС г. Миасс**\n\n"
    "• **Филиалы** — адреса и телефоны\n"
    "• **Справка** — запись, выдача книг, читальный зал, клубы\n"
    "• **Мероприятия** — сайт miasslib.ru\n"
    "• **Поиск книги** — по автору или названию\n"
    "• **Отзыв** — обратная связь\n\n"
    "Сайт: https://miasslib.ru\n"
    "Почта: miasslib@miass.gov74.ru"
)


def load_faq(path: Path) -> list[FaqEntry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        FaqEntry(
            id=e["id"],
            question=e["question"],
            answer=e["answer"],
            keywords=list(e.get("keywords") or []),
        )
        for e in data.get("entries") or []
    ]


def match_faq(text: str, entries: list[FaqEntry], threshold: float = 0.45) -> FaqHit | None:
    q = text.lower().strip()
    if not q:
        return None
    best: FaqHit | None = None
    for entry in entries:
        hits = sum(1 for kw in entry.keywords if kw.lower() in q)
        if hits == 0:
            continue
        score = min(1.0, 0.4 + 0.2 * hits)
        if best is None or score > best.score:
            best = FaqHit(entry=entry, score=score)
    if best and best.score >= threshold:
        return best
    return None
