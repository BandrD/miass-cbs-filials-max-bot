from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BookRecord:
    num: str
    title: str
    author: str

    def blob(self) -> str:
        return f"{self.title} {self.author}".lower()


@dataclass
class BookCatalog:
    path: Path
    records: list[BookRecord]

    @property
    def size(self) -> int:
        return len(self.records)

    def search(self, query: str, *, limit: int = 8) -> list[BookRecord]:
        q = query.lower().strip()
        if not q or not self.records:
            return []
        tokens = [t for t in re.findall(r"[а-яa-z0-9ё]{2,}", q) if t not in {"книг", "книга", "автор", "найди", "поиск"}]
        if not tokens:
            tokens = [q]
        scored: list[tuple[int, BookRecord]] = []
        for rec in self.records:
            blob = rec.blob()
            score = 0
            for t in tokens:
                if t in blob:
                    score += 2 if t in rec.author.lower() or t in rec.title.lower() else 1
            if score:
                scored.append((score, rec))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:limit]]

    def grounding_text(self, hits: list[BookRecord]) -> str:
        if not hits:
            return "В каталоге совпадений не найдено."
        lines = ["Найденные позиции каталога:"]
        for h in hits:
            lines.append(f"• {h.author} — «{h.title}» (№ {h.num})")
        return "\n".join(lines)


def load_book_catalog(path: Path) -> BookCatalog:
    if not path.is_file():
        return BookCatalog(path=path, records=[])
    records: list[BookRecord] = []
    # csv с ; — как в ТЗ
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.reader(text.splitlines(), delimiter=";")
    rows = list(reader)
    if not rows:
        return BookCatalog(path=path, records=[])
    start = 1 if rows and any("автор" in (c or "").lower() for c in rows[0]) else 0
    for row in rows[start:]:
        if len(row) < 3:
            continue
        num, title, author = row[0].strip(), row[1].strip(), row[2].strip()
        if not title and not author:
            continue
        records.append(BookRecord(num=num, title=title, author=author))
    return BookCatalog(path=path, records=records)
