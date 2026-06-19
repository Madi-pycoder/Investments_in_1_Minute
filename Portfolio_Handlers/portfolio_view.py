from aiogram import Router
from aiogram.types import InlineKeyboardButton
from ProjectDataBase.backend import get_goals
from MainMetricsComputingFeatures.shariah import shariah_screen

router = Router()

async def calculate_portfolio_shariah(positions_data):
    total_weight = 0
    halal_weight = 0
    non_compliant = []
    for position in positions_data:
        ticker = position.get("ticker")
        weight = position.get("weight", 0)
        try:
            screening = await shariah_screen({"ticker": ticker})
            total_weight += weight
            if screening["status"] == "HALAL ✅":
                halal_weight += weight
            else:
                non_compliant.append({"ticker": ticker,
                    "weight": weight})
        except Exception:
            continue
    if total_weight == 0:
        return "Not Available"
    percentage = round((halal_weight / total_weight) * 100)
    if percentage >= 90:
        header = f"Passed {percentage}% ✅"
    elif percentage >= 70:
        header = f"Mostly Passed ({percentage}%) ⚠️"
    elif percentage >= 50:
        header = f"Mixed Exposure ({percentage}%) ⚠️"
    else:
        header = f"Limited Compliance ({percentage}%)"
    if not non_compliant:
        return header
    top_non_compliant = sorted(
        non_compliant,
        key=lambda x: x["weight"],
        reverse=True)[:3]
    offenders = "\n".join(
        f"• {item['ticker']} {round(item['weight'] * 100, 1)}%"
        for item in top_non_compliant)
    return (
        f"{header}\n\n"
        f"Top Non-Compliant:\n"
        f"{offenders}")

async def build_portfolio_text(data, metrics, portfolio_id):
    portfolio = data["portfolio"]
    positions_data = (metrics.get("positions_data") or [])
    total_value = (metrics.get("total_value") or 0)
    cash = portfolio.cash
    total_equity = total_value + cash
    risk = (metrics.get("risk") or {})
    volatility = round(risk.get("volatility", 0), 1)
    text = (
        "📊 Portfolio\n\n"
        f"💼 ${round(total_equity, 2)} total\n"
        f"💵 ${round(cash, 2)} cash\n\n")
    goals = await get_goals(portfolio_id)
    goal_results = metrics.get("goal_results") or []
    if goal_results:
        weakest = min(
            goal_results,
            key=lambda x: x["simulation"]["probability"])
        if weakest:
            text += (
                f"🎯 Weakest Goal\n"
                f"🎯 {weakest['goal']['name']}\n"
                f"{weakest['simulation']['probability']}% probability\n\n")
        else:
            text += f"🎯 {len(goals)} active goals\n\n"
        best = max(goal_results, key=lambda
            x: x["simulation"]["probability"])
        if best:
            text += (
                f"🔥 Strongest Goal\n"
                f"🎯 {best['goal']['name']}\n"
                f"{best['simulation']['probability']}% probability\n\n")
        else:
            text += f"🎯 {len(goals)} active goals\n\n"
    else:
        text += "🎯 Add your first goal\n\n"
    risk_label = "Low"
    if volatility >=25:
        risk_label = "High"
    elif volatility >=15:
        risk_label = "Moderate"
    text += f"🛡 Risk: {risk_label}\n"
    shariah_status = await calculate_portfolio_shariah(positions_data)
    text += (f"🕌 Shariah Screen\n"
             f" {shariah_status}\n\n")
    top_positions = sorted(
        positions_data,
        key=lambda x: x.get("value", 0),
        reverse=True)[:7]
    if top_positions:
        text += "📦 Top Positions\n\n"
    qty_map = {p.ticker: p.quantity
            for p in data['positions']}
    for p in top_positions:
        pnl = round(p.get("pnl_pct", 0), 1)
        emoji = (
            "🟢"
            if pnl >= 0
            else "🔴")
        qty = qty_map.get(p["ticker"], 0)
        text += (
            f"{emoji} {p['ticker']} • "
            f"{round(p['weight'] * 100, 1)}%\n"
            f"{round(qty, 4)}\n")
    text += "\n👇 Best next step:\n"

    if volatility > 25:
        text += "⚖️ Reduce concentration risk"
    elif not goals:
        text += "🎯 Add your first goal"
    else:
        text += "🚀 Continue monthly investing"
    keyboard = []
    for p in top_positions:
        qty = round(qty_map.get(p["ticker"], 0), 4)
        keyboard.append([
            InlineKeyboardButton(
                text=f"📉 Sell {p['ticker']}({qty})",
                callback_data=f"sell_{p['ticker']}")])
    keyboard.append([
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu")])
    return text, keyboard