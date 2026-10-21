from __future__ import annotations

import logging
from typing import Any

from app.catalog.books import load_book_catalog
from app.catalog.branches import format_all_branches, format_branch, load_branches, search_branches
from app.config import Settings
from app.llm.faq import HELP_TEXT, load_faq, match_faq
from app.llm.gigachat_client import GigaChatClient
from app.llm.router import answer_book_search, answer_free
from app.llm.text_split import split_text
from app.max_bot.client import MaxClient
from app.max_bot.fsm import DialogState, SessionStore
from app.max_bot.keyboards import cancel_menu, faq_menu, main_menu
from app.storage.store import Storage

logger = logging.getLogger(__name__)


def _chat_id_from_message(message: dict[str, Any]) -> int | None:
    recipient = message.get("recipient") or {}
    chat_id = recipient.get("chat_id")
    if chat_id is not None:
        return int(chat_id)
    sender = message.get("sender") or {}
    if sender.get("user_id") is not None:
        return int(sender["user_id"])
    return None


class BotApp:
    def __init__(
        self,
        settings: Settings,
        client: MaxClient,
        storage: Storage,
        gigachat: GigaChatClient | None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.storage = storage
        self.gigachat = gigachat
        self.sessions = SessionStore()
        self.faq_entries = load_faq(settings.faq_path)
        self.branches = load_branches(settings.branches_path)
        self.catalog = load_book_catalog(settings.books_csv_path)
        self._bg: set[Any] = set()

    def _spawn(self, coro: Any) -> None:
        import asyncio

        task = asyncio.create_task(coro)
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)

    async def send_chunks(
        self,
        chat_id: int,
        text: str,
        *,
        attachments: list | None = None,
    ) -> None:
        chunks = split_text(text)
        for i, chunk in enumerate(chunks):
            atts = attachments if i == 0 else None
            await self.client.send_message(
                chat_id=chat_id,
                text=chunk,
                format="markdown",
                attachments=atts,
            )

    async def send_welcome(self, chat_id: int) -> None:
        text = (
            f"**ЦБС г. {self.branches.city}**\n\n"
            "Справка по филиалам, правилам и поиску книг.\n"
            "Выберите действие:"
        )
        await self.client.send_message(
            chat_id=chat_id,
            text=text,
            format="markdown",
            attachments=[main_menu()],
        )
        self.sessions.set_state(chat_id, DialogState.IDLE)

    async def handle_update(self, update: dict[str, Any]) -> None:
        utype = update.get("update_type")
        try:
            if utype == "bot_started":
                await self.send_welcome(int(update["chat_id"]))
            elif utype == "message_created":
                await self._on_message(update.get("message") or {})
            elif utype == "message_callback":
                await self._on_callback(update)
        except Exception:
            logger.exception("handle_update failed type=%s", utype)

    async def _on_callback(self, update: dict[str, Any]) -> None:
        callback = update.get("callback") or {}
        callback_id = callback.get("callback_id")
        payload = (callback.get("payload") or "").strip()
        message = update.get("message") or {}
        chat_id = _chat_id_from_message(message)
        if chat_id is None and update.get("chat_id") is not None:
            chat_id = int(update["chat_id"])
        if callback_id:
            try:
                await self.client.answer_callback(callback_id, notification="OK")
            except Exception:
                logger.exception("answer_callback failed")
        if chat_id is None:
            return

        if payload == "menu:cancel":
            self.sessions.reset(chat_id)
            await self.send_welcome(chat_id)
            return
        if payload == "menu:help":
            await self.send_chunks(chat_id, HELP_TEXT, attachments=[main_menu()])
            return
        if payload == "menu:branches":
            self.sessions.set_state(chat_id, DialogState.BRANCHES)
            text = format_all_branches(self.branches, limit=12)
            text += (
                "\n\nМожно написать номер филиала или район "
                "(например: «филиал 9», «Тургояк»)."
            )
            await self.send_chunks(chat_id, text, attachments=[cancel_menu()])
            return
        if payload == "menu:faq":
            self.sessions.set_state(chat_id, DialogState.FAQ)
            await self.client.send_message(
                chat_id=chat_id,
                text="**Справка.** Выберите тему или напишите вопрос:",
                format="markdown",
                attachments=[faq_menu()],
            )
            return
        if payload == "menu:events":
            entry = next((e for e in self.faq_entries if e.id == "3"), None)
            text = entry.answer if entry else f"Сайт: {self.branches.site}"
            await self.send_chunks(chat_id, text, attachments=[main_menu()])
            return
        if payload == "menu:book":
            self.sessions.set_state(chat_id, DialogState.WAIT_BOOK)
            note = (
                f"В каталоге сейчас **{self.catalog.size}** позиций "
                f"(`{self.settings.books_csv_path.name}`)."
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=f"Напишите **автора** или **название** книги.\n\n{note}",
                format="markdown",
                attachments=[cancel_menu()],
            )
            return
        if payload == "menu:feedback":
            self.sessions.set_state(chat_id, DialogState.WAIT_FEEDBACK)
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "Напишите отзыв или пожелание одним сообщением.\n"
                    f"Также можно написать на {self.branches.feedback_email}."
                ),
                format="markdown",
                attachments=[cancel_menu()],
            )
            return
        if payload.startswith("faq:"):
            faq_id = payload.split(":", 1)[1]
            entry = next((e for e in self.faq_entries if e.id == faq_id), None)
            if entry:
                await self.send_chunks(
                    chat_id,
                    f"**{entry.question}**\n\n{entry.answer}",
                    attachments=[faq_menu()],
                )
            return

    async def _on_message(self, message: dict[str, Any]) -> None:
        chat_id = _chat_id_from_message(message)
        if chat_id is None:
            return
        sender = message.get("sender") or {}
        if sender.get("is_bot"):
            return
        body = message.get("body") or {}
        text = (body.get("text") or "").strip()
        if not text:
            return
        session = self.sessions.get(chat_id)

        if text in {"/start", "start", "меню", "Меню"}:
            await self.send_welcome(chat_id)
            return

        if session.state == DialogState.WAIT_FEEDBACK:
            self.storage.save_feedback(chat_id, text)
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "Спасибо! Отзыв сохранён.\n"
                    f"Дублировать можно на {self.branches.feedback_email}."
                ),
                format="markdown",
                attachments=[main_menu()],
            )
            self.sessions.set_state(chat_id, DialogState.IDLE)
            return

        if session.state == DialogState.WAIT_BOOK:
            ans = await answer_book_search(
                text,
                catalog=self.catalog,
                gigachat=self.gigachat,
                storage=self.storage,
            )
            await self.send_chunks(chat_id, ans.text, attachments=[main_menu()])
            self.sessions.set_state(chat_id, DialogState.IDLE)
            return

        if session.state == DialogState.BRANCHES:
            hits = search_branches(text, self.branches)
            if hits:
                body_txt = "\n\n".join(format_branch(b) for b in hits)
                await self.send_chunks(chat_id, body_txt, attachments=[main_menu()])
            else:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="Филиал не найден. Попробуйте «филиал 5» или название района.",
                    format="markdown",
                    attachments=[cancel_menu()],
                )
            return

        if session.state == DialogState.FAQ:
            hit = match_faq(text, self.faq_entries)
            if hit:
                await self.send_chunks(
                    chat_id,
                    f"**{hit.entry.question}**\n\n{hit.entry.answer}",
                    attachments=[faq_menu()],
                )
            else:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="Не распознал вопрос. Выберите пункт из списка.",
                    format="markdown",
                    attachments=[faq_menu()],
                )
            return

        # IDLE / free: филиал? FAQ? книга? иначе free
        branch_hits = search_branches(text, self.branches)
        if branch_hits and any(k in text.lower() for k in ("филиал", "адрес", "где", "телефон", "библиотек")):
            body_txt = "\n\n".join(format_branch(b) for b in branch_hits)
            await self.send_chunks(chat_id, body_txt, attachments=[main_menu()])
            return

        faq_hit = match_faq(text, self.faq_entries)
        if faq_hit:
            await self.send_chunks(chat_id, faq_hit.entry.answer, attachments=[main_menu()])
            return

        # эвристика поиска книги
        low = text.lower()
        if any(w in low for w in ("книг", "автор", "произведен", "найди", "толстой", "пушкин")):
            ans = await answer_book_search(
                text,
                catalog=self.catalog,
                gigachat=self.gigachat,
                storage=self.storage,
            )
            await self.send_chunks(chat_id, ans.text, attachments=[main_menu()])
            return

        ans = await answer_free(
            text,
            faq_entries=self.faq_entries,
            gigachat=self.gigachat,
            storage=self.storage,
        )
        await self.send_chunks(chat_id, ans.text, attachments=[main_menu()])
