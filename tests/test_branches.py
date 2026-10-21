from pathlib import Path

from app.catalog.branches import format_branch, load_branches, search_branches

ROOT = Path(__file__).resolve().parents[1]
DATA = load_branches(ROOT / "assets" / "branches.json")


def test_branch_count():
    assert len(DATA.branches) >= 25


def test_search_by_number():
    hits = search_branches("филиал 9", DATA)
    assert hits
    assert hits[0].id == "9"
    assert "Тургояк" in hits[0].address


def test_search_by_place():
    hits = search_branches("Тургояк", DATA)
    assert hits
    assert hits[0].id == "9"


def test_format():
    text = format_branch(DATA.branches[0])
    assert "Либединского" in text or "Центральная" in text
