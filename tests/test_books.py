from pathlib import Path

from app.catalog.books import load_book_catalog

ROOT = Path(__file__).resolve().parents[1]
CAT = load_book_catalog(ROOT / "assets" / "books_sample.csv")


def test_load_sample():
    assert CAT.size >= 15


def test_search_author():
    hits = CAT.search("Толстой")
    assert hits
    assert any("Война и мир" in h.title for h in hits)


def test_search_title():
    hits = CAT.search("Мастер и Маргарита")
    assert hits
    assert "Булгаков" in hits[0].author
