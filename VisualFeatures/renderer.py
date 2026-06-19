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
            "✅ No major portfolio issues detected.", None)
    text = ("🧠 Portfolio Intelligence\n\n"
            "Top opportunities and risks detected:")
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
                f"\n📊 Expected Return\n"
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
        "HALAL ✅": "Passed ✅",
        "MOSTLY HALAL ⚠️": "Mostly Passed ⚠️",
        "MIXED ⚠️": "Mixed Exposure ⚠️",
        "NOT HALAL ❌": "Did Not Pass ❌",
        "UNKNOWN": "Not Available"}
    return mapping.get(status, "Not Available")