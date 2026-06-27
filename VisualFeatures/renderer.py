from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "⚠️",
    "medium": "🧠",
    "low": "✅"}

def classify_goal_gap(delta):
    if delta <= 200:
        return "manageable"
    if delta <= 1000:
        return "challenging"
    if delta <= 5000:
        return "aggressive"
    return "unrealistic"


def render_insight_cards(insights, metrics):
    if not insights:
        return (
            "✅ Проблем в вашем портфеле нет", None)
    text = (
        "🧠 Что можно улучшить\n\n"
        "Мы нашли несколько возможностей повысить доходность или снизить риск:\n\n")
    expected_return = metrics.get("expected_return")
    buttons = []
    for card in insights:
        severity = SEVERITY_EMOJI.get(
            card.severity,
            "•")
        text += (
            f"{severity} {card.headline}\n"
            f"{card.summary}\n")
        if expected_return:
            text += (
                f"\n📈 Потенциальная доходность\n"
                f"{round(expected_return, 1)}% yearly\n")
        if card.action_label and card.callback:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=card.action_label,
                        callback_data=card.callback)])
    keyboard = (
        InlineKeyboardMarkup(
            inline_keyboard=buttons)
        if buttons else None)
    return text, keyboard


def format_shariah(status):
    mapping = {
        "СООТВЕТСТВУЕТ ШАРИАТУ ✅": "Соответствует ✅",
        "Скорее соответствует Шариату ⚠️": "Почти соответствует ⚠️",
        "Нужна дополнительная проверка ⚠️": "Нужна дополнительная проверка ⚠️",
        "НЕ СООТВЕТСТВУЕТ ❌": "Не соответствует ❌",
        "НЕДОСТАТОЧНО ДАННЫХ ⚠️": "Недостаточно данных ⚠️"}
    return mapping.get(status, "Недостаточно данных ⚠️")


def format_money(value):
    if value is None:
        return "Нет данных"
    value = float(value)
    if value >= 1_000_000_000_000:
        return f"${value/1_000_000_000_000:.2f} трлн"
    if value >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f} млрд"
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f} млн"
    if value >= 1_000:
        return f"${value/1_000:.2f} тыс"
    return f"${value:.2f}"


def format_percent(value):
    if value is None:
        return "Нет данных"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "Ошибка данных"


def risk_bar(score):
    if score is None:
        return "⬜⬜⬜⬜⬜"

    filled = round(score / 20)
    return "🟩" * filled + "⬜" * (5 - filled)