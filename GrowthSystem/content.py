from dataclasses import dataclass

@dataclass
class PromoContent:
    text: str
    button_text: str
    button_url: str | None = None

PROMO_CONTENTS: dict[str, list[PromoContent]] = {
    "channel_invite": [
        PromoContent(
            text=(
                "💡 Больше материалов об инвестиция\n\n"
                "В Telegram-канале я делюсь:\n\n"
                "• наблюдениями за рынком;\n"
                "• материалами об инвестициях;\n"
                "• новостями о развитии бота.\n\n"
                "Если интересно — присоединяйтесь 👇"),
            button_text="📚 Посмотреть канал",
            button_url="https://t.me/Investments_in_1Minute")]}

PROMO_CONFIG: dict[str, dict] = {
    "channel_invite": {
        "max_shows": 3,
        "base_cooldown_days": 7,
        "later_cooldown_days": 3}}


def get_content(promo_type: str, index: int) -> PromoContent:
    contents = PROMO_CONTENTS.get(promo_type, [])
    if not contents:
        raise ValueError(f"Unknown promo type: {promo_type}")
    return contents[index % len(contents)]


def get_config(promo_type: str) -> dict:
    config = PROMO_CONFIG.get(promo_type, {})
    if not config:
        raise ValueError(f"Unknown promo type: {promo_type}")
    return config