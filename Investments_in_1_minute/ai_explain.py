def explain_portfolio_logic(positions_data, risk, monte_carlo, goals=None, goal_results=None, top_sector=None, top_sector_weight=0):

    if not positions_data:
        return "No data."

    insights = []
    actions = []

    risk = risk or {}
    monte_carlo = monte_carlo or {}
    top_weight = max(p.get("weight", 0) for p in positions_data)
    vol = risk.get("volatility", 0)
    if monte_carlo:
        expected = monte_carlo.get("expected_return", 0)
        worst = monte_carlo.get("worst_case", 0)
    else:
        expected = 0
        worst = 0


    if top_weight > 0.4:
        insights.append("Your portfolio is highly concentrated in one asset.")

    if len(positions_data) < 4:
        insights.append("You have low diversification across assets.")

    if vol > 25:
        insights.append("Portfolio risk is high with elevated volatility.")
    elif vol < 10:
        insights.append("Portfolio is very stable but may limit growth.")

    if expected > 12:
        insights.append("Strong growth potential detected.")
    elif expected < 5:
        insights.append("Expected returns are relatively low.")

    if worst < -20:
        insights.append("Significant downside risk in worst-case scenarios.")

    if top_sector and top_sector_weight > 0.35:
        insights.append(
            f"Your portfolio is overexposed to {top_sector} ({int(top_sector_weight * 100)}%)."
        )

        if worst < -15:
            insights.append(
                f"This sector concentration increases drawdown risk (~{abs(int(worst))}%)."
            )


    goal_block = ""

    if goals and goal_results:
        goal_block += "\n🎯 Goal Analysis:\n"

        for r in goal_results:
            g = r["goal"]
            prob = r["simulation"]["probability"]

            if prob < 50:
                insights.append(f"You are unlikely to reach '{g['name']}' ({prob}%).")
                actions.append(f"Increase investment or adjust strategy for '{g['name']}'.")

            elif prob < 75:
                insights.append(f"'{g['name']}' is achievable but not secure ({prob}%).")


        worst_goal = min(goal_results, key=lambda x: x["simulation"]["probability"])
        goal_block += (
            f"⚠️ Weakest goal: {worst_goal['goal']['name']} "
            f"({worst_goal['simulation']['probability']}%)\n"
        )


    if top_weight > 0.4:
        actions.append("Reduce exposure to your largest position.")

    if len(positions_data) < 4:
        actions.append("Add more assets to improve diversification.")

    if vol > 25:
        actions.append("Shift part of the portfolio to lower-risk assets.")

    if expected < 5:
        actions.append("Increase allocation to growth-oriented assets.")

    if not actions:
        actions.append("Your portfolio is well balanced.")

    actions = actions[:3]


    score = 100
    if top_weight > 0.4:
        score -= 20
    if vol > 25:
        score -= 20
    if len(positions_data) < 4:
        score -= 15


    text = f"🧠 AI Portfolio Analysis\n\n"
    text += f"📊 Score: {score}/100\n\n"

    text += "🔍 Key Insights:\n"
    for i in insights[:3]:
        text += f"• {i}\n"

    if goal_block:
        text += goal_block + "\n"

    text += "⚖️ Suggested Actions:\n"
    for a in actions:
        text += f"• {a}\n"

    return text
