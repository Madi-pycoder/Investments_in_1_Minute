def explain_portfolio_logic(
    positions_data,
    risk,
    top_sector=None,
    top_sector_weight=0):
    if not positions_data:
        return (
            "📭 Пока нет данных по портфелю.\n"
            "Добавьте или проанализируйте первый актив.")
    text = ("🧠 Разбор Портфеля\n\n"
            "Что удалось заметить:")
    top_weight = max(
        p.get("weight", 0)
        for p in positions_data)
    vol = risk.get("volatility", 0)
    insights = []
    if top_weight > 0.4:
        insights.append(
            "Один актив занимает слишком большую долю портфеля.")
    if len(positions_data) < 4:
        insights.append(
            "Портфель пока недостаточно диверсифицирован.")
    if vol > 25:
        insights.append(
            "Во время просадок стоимость портфеля может сильно колебаться.")
    if top_sector and top_sector_weight > 0.35:
        insights.append(
            f"Доля сектора «{top_sector}» довольно высокая.")
    if not insights:
        insights.append(
            "Портфель выглядит достаточно сбалансированным.")
    for item in insights[:3]:
        text += f"• {item}\n"
    text += "\n💡 Что можно сделать:\n"
    if vol > 25:
        text += "⚖️ Снизить риск портфеля"
    elif len(positions_data) < 4:
        text += "📦 Добавить больше разных активов"
    else:
        text += "🚀 Продолжать долгосрочное инвестирование"
    return text