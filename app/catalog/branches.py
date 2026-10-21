from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Branch:
    id: str
    name: str
    address: str
    phones: list[str]
    keywords: list[str]


@dataclass
class BranchesData:
    city: str
    system: str
    site: str
    feedback_email: str
    admin_phone: str
    branches: list[Branch]


def load_branches(path: Path) -> BranchesData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return BranchesData(
        city=raw.get("city") or "",
        system=raw.get("system") or "",
        site=raw.get("site") or "",
        feedback_email=raw.get("feedback_email") or "",
        admin_phone=raw.get("admin_phone") or "",
        branches=[
            Branch(
                id=str(b["id"]),
                name=b["name"],
                address=b["address"],
                phones=list(b.get("phones") or []),
                keywords=list(b.get("keywords") or []),
            )
            for b in raw.get("branches") or []
        ],
    )


def format_branch(b: Branch) -> str:
    phones = ", ".join(b.phones) if b.phones else "телефон не указан"
    return f"**{b.name}**\n{b.address}\nтел.: {phones}"


def format_all_branches(data: BranchesData, *, limit: int | None = None) -> str:
    items = data.branches if limit is None else data.branches[:limit]
    lines = [f"**Филиалы ЦБС ({data.city})**", ""]
    for b in items:
        phones = ", ".join(b.phones) if b.phones else "—"
        lines.append(f"• {b.name} — {b.address}; тел. {phones}")
    if limit is not None and len(data.branches) > limit:
        lines.append("")
        lines.append(f"_Показаны первые {limit} из {len(data.branches)}. Уточните номер филиала или район._")
    return "\n".join(lines)


def search_branches(query: str, data: BranchesData) -> list[Branch]:
    q = query.lower().strip()
    if not q:
        return []
    # «филиал 9» / «№9» / «филиал № 9»
    m = re.search(r"(?:филиал\s*)?(?:№\s*)?(\d{1,2})\b", q)
    if m:
        num = m.group(1)
        hit = [b for b in data.branches if b.id == num]
        if hit:
            return hit
    scored: list[tuple[int, Branch]] = []
    for b in data.branches:
        score = 0
        blob = f"{b.name} {b.address} {' '.join(b.keywords)}".lower()
        for kw in b.keywords:
            if kw.lower() in q:
                score += 3
        for token in re.findall(r"[а-яa-z0-9]{3,}", q):
            if token in blob:
                score += 1
        if score:
            scored.append((score, b))
    scored.sort(key=lambda x: -x[0])
    return [b for _, b in scored[:5]]
