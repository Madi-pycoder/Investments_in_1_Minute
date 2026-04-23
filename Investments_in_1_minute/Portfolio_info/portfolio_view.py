def build_portfolio_text(data, metrics):
    portfolio = data["portfolio"]
    positions_data = metrics["positions_data"]

    total_value = metrics["total_value"]
    cash = portfolio.cash
    total_equity = total_value + cash

    text = (
        f"📊 Portfolio Overview\n\n"
        f"💰 Cash: ${round(cash, 2)}\n"
        f"💼 Equity: ${round(total_equity, 2)}\n\n"
    )

    # 📦 POSITIONS
    text += "📦 Positions\n\n"
    for p in positions_data:
        pnl = round(p.get("pnl_pct", 0), 1)

        emoji = "🟢" if pnl >= 0 else "🔴"

        text += f"{p['ticker']} — ${round(p['value'], 2)} ({emoji} {pnl}%)\n"

    if metrics.get("top_gainers") or metrics.get("top_losers"):
        text += "\n🔥 Top Movers\n\n"

        if metrics.get("top_gainers"):
            text += "🟢 Gainers:\n"
            for p in metrics["top_gainers"]:
                text += f"{p['ticker']} (+{round(p['pnl_pct'], 1)}%)\n"

        if metrics.get("top_losers"):
            text += "\n🔴 Losers:\n"
            for p in metrics["top_losers"]:
                text += f"{p['ticker']} ({round(p['pnl_pct'], 1)}%)\n"

    # ⚠️ ALERTS
    if metrics["alerts"]:
        text += "\n⚠️ Alerts:\n"
        for a in metrics["alerts"]:
            text += f"- {a}\n"

    # ⚖️ ACTIONS
    if metrics["shariah_rebalance"]:
        text += "\n⚖️ Actions:\n"
        for t in metrics["shariah_rebalance"][:3]:
            text += f"{t['action']} ${round(t['amount'], 2)} {t['ticker']}\n"

    # 🤖 IDEAS
    text += "\n🤖 Ideas\n\n"

    if metrics["halal"]:
        text += "🌙 Halal:\n"
        for t, w in list(metrics["halal"].items())[:3]:
            text += f"{t}: {round(w * 100, 1)}%\n"

    if metrics["sharpe"]:
        text += "\n📊 Sharpe:\n"
        for t, w in list(metrics["sharpe"].items())[:3]:
            text += f"{t}: {round(w * 100, 1)}%\n"

    # 📊 RISK
    if metrics.get("risk") and metrics["risk"].get("risk_score") is not None:
        text += f"\n📊 Risk: {metrics['risk']['risk_score']}/100"

    mc = metrics.get("monte_carlo")

    if mc and mc.get("expected_return") is not None:
        text += "\n📊 Risk & Simulation\n\n"
        text += f"Expected: {mc['expected_return']}%\n"

        if mc.get("worst_case") is not None:
            text += f"Worst: {mc['worst_case']}%\n"


    if metrics.get("goal_results"):
        text += "\n\n🎯 Goals\n\n"

        for r in metrics["goal_results"]:
            g = r["goal"]
            sim = r["simulation"]
            analysis = r["analysis"]

            text += (
                f"{g['name']}\n"
                f"{sim['probability']}% | ${analysis['monthly_needed']}/mo\n\n"
            )


    if metrics.get("what_if"):
        text += "\n🔮 What If Analysis\n\n"
        for s in metrics["what_if"]:
            delta = s.get("delta", 0)
            delta_str = f"(+{delta}%)" if delta > 0 else f"({delta}%)"

            text += f"{s['scenario']}: {s['probability']}% {delta_str}\n"

    if metrics.get("nudges"):
        text += "\n🧠 AI Coach\n\n"

        for n in metrics["nudges"]:
            emoji = {
                "critical": "🚨",
                "improve": "⚠️",
                "good": "✅"
            }.get(n["type"], "•")

            text += f"{emoji} {n['text']}\n"

    return text
