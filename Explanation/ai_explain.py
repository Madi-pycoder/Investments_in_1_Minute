def explain_portfolio_logic(
    positions_data,
    risk,
    top_sector=None,
    top_sector_weight=0
):
    if not positions_data:
        return (
            "📭 No portfolio data yet.\n"
            "Analyze your first investment to begin."
        )
    text = ("🧠 Portfolio Intelligence\n\n"
            "Top opportunities and risks detected:")
    top_weight = max(
        p.get("weight", 0)
        for p in positions_data
    )
    vol = risk.get("volatility", 0)
    insights = []
    if top_weight > 0.4:
        insights.append(
            "One position dominates your portfolio."
        )
    if len(positions_data) < 4:
        insights.append(
            "Your diversification is still limited."
        )
    if vol > 25:
        insights.append(
            "Portfolio swings may feel stressful during market drops."
        )
    if top_sector and top_sector_weight > 0.35:
        insights.append(
            f"{top_sector} exposure is relatively high."
        )
    if not insights:
        insights.append(
            "Your portfolio currently looks reasonably balanced."
        )
    for item in insights[:3]:
        text += f"• {item}\n"
    text += "\n👇 Suggested next step:\n"
    if vol > 25:
        text += "⚖️ Reduce portfolio risk"
    elif len(positions_data) < 4:
        text += "📦 Improve diversification"
    else:
        text += "🚀 Continue long-term investing"
    return text