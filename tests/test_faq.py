from pathlib import Path

from app.llm.faq import load_faq, match_faq

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = load_faq(ROOT / "assets" / "faq.json")


def test_registration():
    hit = match_faq("Как записаться в библиотеку?", ENTRIES)
    assert hit is not None
    assert hit.entry.id == "1.2"


def test_clubs():
    hit = match_faq("Какие клубы есть?", ENTRIES)
    assert hit is not None
    assert "Дилижанс" in hit.entry.answer


def test_events():
    hit = match_faq("Где смотреть выставки и мероприятия?", ENTRIES)
    assert hit is not None
    assert "miasslib.ru" in hit.entry.answer
