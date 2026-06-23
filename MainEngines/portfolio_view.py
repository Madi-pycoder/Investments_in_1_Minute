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
            if screening["status"] == "СООТВЕТСВУЕТ ШАРИАТУ ✅":
                halal_weight += weight
            else:
                non_compliant.append({"ticker": ticker,
                    "weight": weight})
        except Exception:
            continue
    if total_weight == 0:
        return "Не доступно"
    percentage = round((halal_weight / total_weight) * 100)
    if percentage >= 90:
        header = f"Соответсвует Шариату {percentage}% ✅"
    elif percentage >= 70:
        header = f"В основном соответствует Шариату ({percentage}%) ⚠️"
    elif percentage >= 50:
        header = f"Есть спорные активы ({percentage}%) ⚠️"
    else:
        header = f"Низкий уровень соответствия ({percentage}%)"
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
        f"Основные несоответствующие активы:\n"
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
        "📊 Ваш портфель\n\n"
        f"💼 Общая стоиомсть: ${round(total_equity, 2)}\n"
        f"💵 Свободные средства: ${round(cash, 2)}\n\n")
    goals = await get_goals(portfolio_id)
    goal_results = metrics.get("goal_results") or []
    if goal_results:
        weakest = min(
            goal_results,
            key=lambda x: x["simulation"]["probability"])
        if weakest:
            text += (
                f"🎯 Цель с наименьшими шансами\n"
                f"🎯 {weakest['goal']['name']}\n"
                f"Вероятность достижения: {weakest['simulation']['probability']}%\n\n")
        else:
            text += f"🎯 Количество целей: {len(goals)}\n\n"
        best = max(goal_results, key=lambda
            x: x["simulation"]["probability"])
        if best:
            text += (
                f"🔥 Самая уверенная цель\n"
                f"🎯 {best['goal']['name']}\n"
                f"Вероятность достижения: {best['simulation']['probability']}%\n\n")
        else:
            text += f"🎯 Количесвто целей: {len(goals)}\n\n"
    else:
        text += "🎯 Добавьте первую финансовую цель\n\n"
    risk_label = "Низкий"
    if volatility >=25:
        risk_label = "Высокий"
    elif volatility >=15:
        risk_label = "Умеренный"
    text += f"🛡 Уровень риска: {risk_label}\n"
    shariah_status = await calculate_portfolio_shariah(positions_data)
    text += (f"🕌 Соответсвие Шариату:\n"
             f" {shariah_status}\n\n")
    top_positions = sorted(
        positions_data,
        key=lambda x: x.get("value", 0),
        reverse=True)[:7]
    if top_positions:
        text += "📦 Крупнейшие позиции\n\n"
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
    text += "\n👇 Что можно сделать сейчас:\n"

    if volatility > 25:
        text += "⚖️ Снизить зависимость от отдельных активов"
    elif not goals:
        text += "🎯 Добавить первую финансовую цель"
    else:
        text += "🚀 Продолжать регулярные инвестиции"
    keyboard = []
    for p in top_positions:
        qty = round(qty_map.get(p["ticker"], 0), 4)
        keyboard.append([
            InlineKeyboardButton(
                text=f"📉 Продать {p['ticker']}({qty})",
                callback_data=f"sell_{p['ticker']}")])
    keyboard.append([
        InlineKeyboardButton(
            text="🏠 Главное Меню",
            callback_data="main_menu")])
    return text, keyboard