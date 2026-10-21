from __future__ import annotations

from typing import Any


def _rows(buttons: list[dict[str, Any]], per_row: int = 1) -> list[list[dict[str, Any]]]:
    return [buttons[i : i + per_row] for i in range(0, len(buttons), per_row)]


def main_menu() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {"type": "callback", "text": "Филиалы", "payload": "menu:branches"},
                    {"type": "callback", "text": "Справка", "payload": "menu:faq"},
                ],
                [
                    {"type": "callback", "text": "Поиск книги", "payload": "menu:book"},
                    {"type": "callback", "text": "Мероприятия", "payload": "menu:events"},
                ],
                [
                    {"type": "callback", "text": "Оставить отзыв", "payload": "menu:feedback"},
                    {"type": "callback", "text": "Помощь", "payload": "menu:help"},
                ],
            ]
        },
    }


def cancel_menu() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [[{"type": "callback", "text": "В меню", "payload": "menu:cancel"}]],
        },
    }


def faq_menu() -> dict[str, Any]:
    buttons = [
        {"type": "callback", "text": "Запись в библиотеку", "payload": "faq:1.2"},
        {"type": "callback", "text": "Выдача и возврат", "payload": "faq:1.3"},
        {"type": "callback", "text": "Читальный зал", "payload": "faq:1.4"},
        {"type": "callback", "text": "Клубы", "payload": "faq:1.5"},
        {"type": "callback", "text": "В меню", "payload": "menu:cancel"},
    ]
    return {"type": "inline_keyboard", "payload": {"buttons": _rows(buttons, 1)}}
