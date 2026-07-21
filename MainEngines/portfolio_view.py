from aiogram import Router
from aiogram.types import InlineKeyboardButton
from ProjectDataBase.backend import get_goals
import logging

logger = logging.getLogger(__name__)
router = Router()

async def calculate_portfolio_shariah(positions_data):
    total_weight = 0
    halal_weight = 0
    non_compliant = []
    for position in positions_data:
        weight = position["weight"]
        try:
            total_weight += weight
            if position.get("shariah_compliant"):
                halal_weight += weight
            else:
                non_compliant.append({"ticker": position["ticker"], "weight": weight})
        except Exception as e:
            logger.info("SHARIAH ERROR:", position["ticker"], e)
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
        f"📈 Инвестировано: ${round(total_equity-cash, 2)}\n"
        f"💵 Свободные средства: ${round(cash, 2)}\n\n")
    goals = await get_goals(portfolio_id)
    goal_results = metrics.get("goal_results") or []
    if len(goal_results) == 1:
        only = goal_results[0]
        text += (
            f"🎯 Главная цель\n"
            f"🎯 {only['goal']['name']}\n"
            f"Вероятность достижения: "
            f"{only['simulation']['probability']}%\n\n")
    elif len(goal_results) > 1:
        weakest = min(
            goal_results,
            key=lambda x: x["simulation"]["probability"])
        best = max(
            goal_results,
            key=lambda x: x["simulation"]["probability"])
        text += (
            f"🎯 Цель с наименьшими шансами\n"
            f"🎯 {weakest['goal']['name']}\n"
            f"Вероятность достижения: "
            f"{weakest['simulation']['probability']}%\n\n")
        text += (
            f"🔥 Самая уверенная цель\n"
            f"🎯 {best['goal']['name']}\n"
            f"Вероятность достижения: "
            f"{best['simulation']['probability']}%\n\n")
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