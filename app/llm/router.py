from __future__ import annotations

import logging
from dataclasses import dataclass

from app.catalog.books import BookCatalog
from app.llm.faq import FaqEntry, match_faq
from app.llm.gigachat_client import GigaChatClient
from app.storage.store import Storage

logger = logging.getLogger(__name__)


@dataclass
class TextAnswer:
    text: str
    source: str


async def answer_book_search(
    query: str,
    *,
    catalog: BookCatalog,
    gigachat: GigaChatClient | None,
    storage: Storage | None = None,
) -> TextAnswer:
    hits = catalog.search(query)
    local = catalog.grounding_text(hits)

    if gigachat is not None and gigachat.ready:
        prompt = (
            f"Запрос читателя: {query}\n\n"
            f"{local}\n\n"
            "Кратко ответь, какие издания из каталога подходят. "
            "Не добавляй книги вне списка."
        )
        try:
            reply = await gigachat.ask(prompt)
            if storage is not None:
                storage.log_token_usage(
                    prompt_tokens=reply.prompt_tokens,
                    completion_tokens=reply.completion_tokens,
                    total_tokens=reply.total_tokens,
                    note="book_search",
                )
            return TextAnswer(text=f"{reply.text}\n\n---\n{local}", source="gigachat")
        except Exception:
            logger.exception("GigaChat book search failed")
            return TextAnswer(
                text=f"GigaChat недоступен. Результат локального поиска:\n\n{local}",
                source="fallback",
            )

    if hits:
        return TextAnswer(
            text=(
                f"{local}\n\n"
                "_GigaChat выключен — показан только локальный поиск по каталогу._"
            ),
            source="catalog",
        )
    return TextAnswer(
        text=(
            "В каталоге совпадений не найдено. "
            "Уточните автора или название. "
            "Полный CSV-справочник передаёт заказчик (`BOOKS_CSV_PATH`)."
        ),
        source="fallback",
    )


async def answer_free(
    text: str,
    *,
    faq_entries: list[FaqEntry],
    gigachat: GigaChatClient | None,
    storage: Storage | None = None,
) -> TextAnswer:
    hit = match_faq(text, faq_entries)
    if hit:
        return TextAnswer(text=hit.entry.answer, source="faq")
    if gigachat is not None and gigachat.ready:
        try:
            reply = await gigachat.ask(text)
            if storage is not None:
                storage.log_token_usage(
                    prompt_tokens=reply.prompt_tokens,
                    completion_tokens=reply.completion_tokens,
                    total_tokens=reply.total_tokens,
                    note="free",
                )
            return TextAnswer(text=reply.text, source="gigachat")
        except Exception:
            logger.exception("GigaChat free failed")
    return TextAnswer(
        text=(
            "Не нашёл готовый ответ в справке. "
            "Выберите пункт меню или включите GigaChat (`GIGACHAT_ENABLED=true`)."
        ),
        source="fallback",
    )
