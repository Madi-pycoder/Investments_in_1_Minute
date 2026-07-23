from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from Portfolio_info.portfolio_compute import compute_portfolio_metrics
from Portfolio_info.portfolio_data import load_portfolio_data
from ProjectDataBase.analytics import AnalyticsService, build_portfolio_event_data
from ProjectDataBase.cache import diagnosis_cache, rebalance_preview_cache, goal_fix_preview_cache, \
    portfolio_data_cache, PORTFOLIO_VIEW_CACHE
from MainEngines.portfolio_rebalance import calculate_rebalance
from MarketFeatures.market import get_stocks_batch
from ProjectDataBase.market_data_service import get_bulk_prices
from MainMetricsComputingFeatures.riskmanagement import (calculate_portfolio_risk, calculate_portfolio_volatility, calculate_optimal_weights)
from MainEngines.shariah_optimizer import optimize_shariah_portfolio
from MainEngines.goal_engine import (optimize_portfolio_for_goals,
                                     build_goal_based_weights, simulate_multiple_goals)
from ProjectDataBase import backend as rq
from VisualFeatures import keyboards as kb
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class ProfileSetup(StatesGroup):
    income = State()
    budget = State()
    risk = State()
router = Router()

async def preload_diagnosis(portfolio_id, data):
    try:
        metrics = await compute_portfolio_metrics(data)
        diagnosis_cache[portfolio_id] = {"data": metrics, "ts": time.time()}
    except Exception as e:
        logger.error("preload_diagnosis ERROR: %s", e)


def get_diagnosis_cached(portfolio_id):
    item = diagnosis_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > 60:
        return None
    return item["data"]

def safe_percent(v):
    return round(v, 2) if isinstance(v, (int, float)) else 0

async def compare_portfolios(current_positions, target_weights):
    current_risk = await calculate_portfolio_risk(current_positions)
    total_value = sum(p["value"] for p in current_positions)
    rebalanced_positions = []
    for p in current_positions:
        ticker = p["ticker"]
        target_weight = target_weights.get(ticker, 0)
        rebalanced_positions.append({
            "ticker": ticker,
            "value": total_value * target_weight,
            "weight": target_weight})
    rebalanced_risk = await calculate_portfolio_risk(rebalanced_positions)
    rebalanced_return = current_risk.get("expected_return", 8)
    return {
        "current": {
            "return": safe_percent(current_risk.get("expected_return", 0)),
            "risk": current_risk.get("volatility")},
        "rebalanced": {
            "return": safe_percent(rebalanced_return),
            "risk": rebalanced_risk.get("volatility")}}


def build_rebalance_preview(trades, comparison):
    buy_lines=[]
    sell_lines=[]
    for t in trades:
        line = f"• {t['ticker']} → ${round(t['amount'], 2)}"
        if t["action"].upper() == "BUY":
            buy_lines.append(line)
        else:
            sell_lines.append(line)
    text = ("⚖️ Как можно улучшить портфель\n\n"
            "Чтобы снизить лишний риск и сделать портфель более устойчивым:")
    if sell_lines:
        text += "📉 Уменьшить долю:\n"
        text += "\n".join(sell_lines)
        text += "\n\n"
    if buy_lines:
        text += "📈 Увеличить долю:\n"
        text += "\n".join(buy_lines)
        text += "\n\n"

    if comparison:
        current_risk = round(comparison["current"]["risk"] or 0, 1)
        new_risk = round(comparison["rebalanced"]["risk"] or 0, 1)
        text += (
            "🛡 Ожидаемый эффект\n"
            f"Уровень Риска: {current_risk}% → {new_risk}%\n\n")
    text += (
        "Что это даст:\n"
        "• меньше зависимость от одной компании\n"
        "• спокойнее переживать падения рынка\n"
        "• более стабильный рост капитала со временем")
    return text


async def rebalance_now(callback: CallbackQuery, state: FSMContext):
    await callback.answer("⚖️ Подбираю более сбалансированное распределение...")
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    cached_metrics = get_diagnosis_cached(portfolio_id)
    positions = await rq.get_positions(portfolio_id)
    if not positions:
        await callback.message.answer(
        "📭 В портфеле пока нет активов.\n\n"
        "Введите тикер компании\n\n"
        "ИЛИ выберите готовую подборку 👇", reply_markup=kb.stock_categories)
        return
    tickers = [p.ticker for p in positions]
    stocks_batch = await get_stocks_batch(tickers)
    prices_dict = await get_bulk_prices(tickers)
    positions_data = []
    total_value = 0
    for p in positions:
        price = prices_dict.get(p.ticker)
        if price is None:
            continue
        value = p.quantity * price
        total_value += value
        positions_data.append({
            "ticker": p.ticker,
            "value": value})
    for p in positions_data:
        p["weight"] = p["value"] / total_value if total_value else 0
    goals = await rq.get_goals(portfolio_id)
    has_shariah = any(getattr(g, "compliance", None) == "shariah" for g in goals)
    if has_shariah:
        target_weights = await optimize_shariah_portfolio(
            positions_data,
            stocks_batch)
    else:
        target_weights = await calculate_optimal_weights(positions_data)
    rebalance_result = calculate_rebalance(positions_data, target_weights, total_value)
    trades = rebalance_result["trades"]
    skipped_small = rebalance_result["skipped_small"]
    if not trades:
        if skipped_small > 0:
            await callback.message.answer(
                "✅ Сейчас серьёзная ребалансировка не требуется.\n\n"
                "Портфель близок к целевому распределению.")
        else:
            await callback.message.answer("✅ Портфель уже хорошо сбалансирован.")
        return
    if cached_metrics:
        comparison = {
            "current": {
                "risk": cached_metrics.get("portfolio_volatility"),
                "return": cached_metrics.get("expected_return", 0)}}
        rebalanced_positions = [
            {
                "ticker": p["ticker"],
                "weight": target_weights.get(p["ticker"], 0)}
            for p in positions_data]
        new_risk = await calculate_portfolio_volatility(rebalanced_positions)
        comparison["rebalanced"] = {
            "risk": new_risk,
            "return": cached_metrics.get("expected_return", 0)}
    else:
        comparison = await compare_portfolios(positions_data, target_weights)
    rebalance_preview_cache[portfolio_id] = {
        "trades": trades,
        "prices_dict": prices_dict}
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Применить изменения",
                callback_data="confirm_rebalance")]])
    text_preview = build_rebalance_preview(trades, comparison)
    await callback.message.answer(
        text_preview,
        reply_markup=keyboard)
    asyncio.create_task(AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="rebalance.created",
            category="portfolio",
            event_data=build_portfolio_event_data(
                portfolio_id=portfolio_id,
                positions=positions,
                goals=goals,
                metrics=cached_metrics,
                total_value=total_value,
                cached_metrics=bool(cached_metrics),
                extra={
                    "trades_count": len(trades),
                    "skipped_small": skipped_small,
                    "has_shariah": has_shariah})))

@router.callback_query(F.data == "confirm_rebalance")
async def confirm_rebalance(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    preview = rebalance_preview_cache.get(portfolio_id)
    if not preview:
        await callback.message.answer("⚠️ Сессия просрочена\n\n"
            "Попробуйте позже")
        return
    await rq.execute_rebalance(
        portfolio_id,
        preview["trades"])
    await callback.message.answer(
        "✅ Ребалансировка выполнена\n\n"
        "Портфель приведён к более устойчивому распределению.\n"
        "Теперь риск лучше сбалансирован, а структура ближе к вашим целям.")
    rebalance_preview_cache.pop(portfolio_id, None)
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="rebalance.confirmed",
            category="portfolio",
            event_data={"portfolio_id": portfolio_id,
                "trades_count": len(preview["trades"]),
                "cache_hit": True}))



@router.callback_query(F.data == "goal_fix")
async def goal_fix(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.message.answer("⚡ Анализирую портфель и ищу лучший путь к вашей цели...")
    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")
    if portfolio_id is not None:
        portfolio_id = int(portfolio_id)
    data = await load_portfolio_data(portfolio_id)
    metrics = get_diagnosis_cached(portfolio_id)
    if not metrics:
        data = await load_portfolio_data(portfolio_id)
        metrics = await AnalyticsService.measure(
            user_id,
            "metrics.compute",
            compute_portfolio_metrics(data),
            category="performance",
            event_data={
                "portfolio_id": portfolio_id,
                "positions": len(data.get("positions") or []),
                "goals": len(data.get("goals") or [])})
    positions = data.get("positions") or []
    if not positions:
        await callback.message.answer("📭 В портфеле пока нет активов.\n\n"
            "Введите тикер компании\n\n"
            "ИЛИ выберите готовую подборку 👇", reply_markup=kb.stock_categories)
        return
    if not metrics:
        await callback.message.answer(
            "⚠️ Часть рыночных данных сейчас недоступна.\n\n"
            "МЫ всё равно выполняем анализ, но некоторые рекомендации могут быть менее точными.")
        return
    goals = await rq.get_goals(portfolio_id)
    if not goals:
        await rebalance_now(callback, state)
        return
    positions_data = metrics.get("positions_data") or []
    total_value = metrics.get("total_value") or 0
    optimizations = await asyncio.to_thread(
        optimize_portfolio_for_goals,
        positions_data, total_value, goals)
    if not optimizations:
        await callback.message.answer("❌ 📊 Пока не вижу изменений, которые заметно улучшат результат\n"
            "Возможные причины:\n"
            "• слишком мало активов\n"
            "• ещё не добавлены финансовые цели\n"
            "• недостаточно данных для анализа")
        return
    best = optimizations[0]
    target_weights = build_goal_based_weights(
        positions_data,
        goals, best["risk"])
    logger.debug("POSITIONS: %s", [p["ticker"] for p in positions_data])
    logger.debug("TARGET: %s", target_weights)
    portfolio_volatility = (metrics.get("risk", {}).get("volatility", 15))/100
    goal_analysis = simulate_multiple_goals(positions_data, total_value, goals,
        portfolio_volatility, monthly_contribution=0)
    old_prob = metrics["goal_results"][0]["simulation"]["probability"]
    old_risk = metrics.get("portfolio_volatility")
    new_goal_analysis = simulate_multiple_goals(positions_data, total_value,
        goals, portfolio_volatility, monthly_contribution=0)
    new_prob = new_goal_analysis[0]["simulation"]["probability"]
    new_risk = best["risk"] * 100
    logger.debug("Target weights: %s", target_weights)
    rebalance_result = calculate_rebalance(positions_data, target_weights, total_value)
    trades = rebalance_result["trades"]
    best_prob = best.get("raw_probability", 0)
    if not trades:
        if best_prob < 50:
            await callback.message.answer(
                "⚠️ Структура портфеля уже близка к оптимальной."
                "Чтобы повысить вероятность достижения цели, рассмотрите:"
                "• увеличение ежемесячных инвестиций"
                "• более долгий срок достижения цели"
                "• дополнительный стартовый капитал")
        else:
            await callback.message.answer(
                "✅ Портфель уже находится в хорошем состоянии\n\n"
                "Сейчас серьёзных изменений не требуется\n"
                "Продолжайте придерживаться выбранной стратегии.")
        return
    goal_fix_preview_cache[portfolio_id] = {
        "trades": trades,
        "prices_dict": data["prices_dict"],
        "old_prob": old_prob,
        "new_prob": new_prob,
        "old_risk": old_risk,
        "new_risk": new_risk,
        "monthly_boost": best["monthly_boost"]}
    buy_lines = []
    sell_lines = []
    for t in trades:
        line = f"• {t['ticker']} → ${round(t['amount'], 2)}"
        if t["action"].upper() == "BUY":
            buy_lines.append(line)
        else:
            sell_lines.append(line)
    text = ("🎯 План достижения цели\n\n"
            "Вот что можно изменить, чтобы увеличить вероятность достижения вашей цели")
    progress = metrics.get("goal_progress", [])
    if progress:
        item = progress[0]
        text += (
            f"📈 Сейчас выполнено: "
            f"{int(item['progress_now'] * 100)}%\n\n")
    if sell_lines:
        text += "📉 Уменьшить долю:\n"
        text += "\n".join(sell_lines)
        text += "\n\n"
    if buy_lines:
        text += "📈 Увеличить долю:\n"
        text += "\n".join(buy_lines)
        text += "\n\n"
    text += (
        f"🎯 Вероятность достижения цели\n"
        f"Сейчас: {old_prob:.0f}%\n")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                    text="✅ Применить план",
                    callback_data="confirm_goal_fix")]])
    logger.debug("PORTFOLIO VIEW: %s", metrics.get("goal_results"))
    logger.debug("GOAL FIX: %s", goal_analysis)
    await callback.message.answer(text, reply_markup=keyboard)



@router.callback_query(F.data == "confirm_goal_fix")
async def confirm_goal_fix(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    preview = goal_fix_preview_cache.get(portfolio_id)
    if not preview:
        await callback.message.answer("⚠️ Goal Fix session expired.")
        return
    await rq.execute_rebalance(
        portfolio_id,
        preview["trades"])
    await callback.message.answer(
        "✅ План применён\n\n"
        "📊 Пересчитываю показатели портфеля...")
    portfolio_data_cache.pop(portfolio_id, None)
    diagnosis_cache.pop(portfolio_id, None)
    PORTFOLIO_VIEW_CACHE.pop(portfolio_id, None)
    data = await load_portfolio_data(portfolio_id)
    metrics = await compute_portfolio_metrics(data)
    new_prob = metrics["goal_results"][0]["simulation"]["probability"]
    new_risk = metrics["portfolio_volatility"]
    await callback.message.answer(
        "✅ План применён\n\n"
        f"🎯 Вероятность достижения цели\n"
        f"{preview['old_prob']:.0f}% → {new_prob:.0f}%\n\n"
        f"📊 Волатильность\n"
        f"{preview['old_risk']:.0f}% → {new_risk:.0f}%")
    diagnosis_cache.pop(portfolio_id, None)