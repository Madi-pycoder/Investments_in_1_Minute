from aiogram.utils.keyboard import InlineKeyboardBuilder


def review_rating_keyboard():
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(
            text=f"{i}⭐",
            callback_data=f"review_rating:{i}")
    kb.adjust(5)
    return kb.as_markup()


def review_finish_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✍️ Написать ещё",
        callback_data="review_again")
    kb.button(
        text="🏠 Главное меню",
        callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()