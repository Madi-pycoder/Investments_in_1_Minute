from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from Portfolio_info.portfolio_compute import compute_portfolio_metrics
from Portfolio_info.portfolio_data import load_portfolio_data
from ProjectDataBase.analytics import AnalyticsService, build_portfolio_event_data
from ProjectDataBase.cache import diagnosis_cache, rebalance_preview_cache, goal_fix_preview_cache
from Portfolio_Handlers.portoflio_rebalance import calculate_rebalance
from MarketFeatures.market import get_stocks_batch
from ProjectDataBase.market_data_service import get_bulk_prices
from MainMetricsComputingFeatures.riskmanagement import (calculate_portfolio_risk, calculate_portfolio_volatility, calculate_optimal_weights)
from Portfolio_Handlers.shariah_optimizer import optimize_shariah_portfolio
from MainEngines.goal_engine import (optimize_portfolio_for_goals,
                                     build_goal_based_weights, simulate_multiple_goals)
from ProjectDataBase import backend as rq
from VisualFeatures import keyboards as kb
import asyncio
import time

class ProfileSetup(StatesGroup):
    income = State()
    budget = State()
    risk = State()

router = Router()

async def preload_diagnosis(portfolio_id,data):
    try:
        metrics = await compute_portfolio_metrics(data)
        diagnosis_cache[portfolio_id] = {"data": metrics, "ts": time.time()}
    except Exception as e:
        print("preload_diagnosis ERROR:", e)


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
    text = ("⚖️ Portfolio Optimization\n\n"
            "Suggested allocation adjustments:")
    if sell_lines:
        text += "📉 Reduce:\n"
        text += "\n".join(sell_lines)
        text += "\n\n"
    if buy_lines:
        text += "📈 Increase:\n"
        text += "\n".join(buy_lines)
        text += "\n\n"

    if comparison:
        current_risk = round(comparison["current"]["risk"] or 0, 1)
        new_risk = round(comparison["rebalanced"]["risk"] or 0, 1)
        text += (
            "🛡 Expected impact\n"
            f"Risk: {current_risk}% → {new_risk}%\n\n")
    text += (
        "Why this may help:\n"
        "• better diversification\n"
        "• lower concentration risk\n"
        "• improved long-term consistency")
    return text


async def rebalance_now(callback: CallbackQuery, state: FSMContext):
    await callback.answer("⚖️ Optimizing risk-adjusted allocation...")
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    cached_metrics = get_diagnosis_cached(portfolio_id)
    positions = await rq.get_positions(portfolio_id)
    if not positions:
        await callback.message.answer(
        "📭 Your portfolio is empty\n"
        "Most users start with:\n"
        "• MSFT - Microsoft\n"
        "• AAPL - Apple\n"
        "• NVDA - Nvidia\n"
        "• TSLA - Tesla", reply_markup=kb.popular_stocks)
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
                "ℹ️ No major rebalance needed right now. "
                "Small concentration issues still exist, "
                "but current drift is below rebalance threshold.")
        else:
            await callback.message.answer("✅ Portfolio already balanced.")
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
            [
                InlineKeyboardButton(
                    text="✅ Apply Changes",
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
        await callback.message.answer("⚠️ Rebalance session expired.")
        return
    await rq.execute_rebalance(
        portfolio_id,
        preview["trades"],
        preview["prices_dict"])
    await callback.message.answer(
        "✅ Portfolio updated successfully.\n\n"
        "Your allocation is now more balanced.")
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
    await callback.answer("⚡ Optimizing...")
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
        await callback.message.answer("📭 Your portfolio is empty\n"
                                      "Most users start with:\n"
                                      "• SPUS (Halal S&P 500)\n"
                                      "• HLAL (Halal US equities)\n"
                                      "• AAPL\n"
                                      "• NVDA")
        return
    if not metrics:
        await callback.message.answer(
            "⚠️ Data temporarily unavailable\n"
            "Showing simplified view")
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
        await callback.message.answer("❌ Can't improve this portfolio yet.\n"
                                      "Usually this happens when:\n"
                                      "• portfolio is too small\n"
                                      "• goals are missing\n"
                                      "• positions need more diversification")
        return
    best = optimizations[0]
    print("POSITIONS_DATA:")
    print("REAL POSITIONS")
    print([p["ticker"] for p in positions_data])
    for p in positions_data:
        print(p["ticker"])
    target_weights = build_goal_based_weights(
        positions_data,
        goals, best["risk"])
    print("POSITIONS:")
    print([p["ticker"] for p in positions_data])
    print("TARGET:")
    print(target_weights)
    portfolio_volatility = (metrics.get("risk", {}).get("volatility", 15))/100
    goal_analysis = simulate_multiple_goals(positions_data, total_value, goals,
        portfolio_volatility)
    old_prob = metrics["goal_results"][0]["simulation"]["probability"]
    old_risk = metrics.get("portfolio_volatility")
    new_goal_analysis = simulate_multiple_goals(positions_data, total_value,
        goals, best["risk"])
    new_prob = new_goal_analysis[0]["simulation"]["probability"]
    new_risk = best["risk"] * 100
    print(target_weights)
    rebalance_result = calculate_rebalance(positions_data, target_weights, total_value)
    trades = rebalance_result["trades"]
    best_prob = best.get("raw_probability", 0)
    if not trades:
        if best_prob < 50:
            await callback.message.answer(
                "⚠️ Portfolio allocation is already near optimal,\n"
                "but your goal still may require:\n"
                "• higher monthly investing\n"
                "• longer timeline\n"
                "• larger starting capital")
        else:
            await callback.message.answer(
                "✅ Portfolio is already close to optimal.\n\n"
                "No major changes needed.")
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
    text = ("🎯 Goal Recovery Plan\n\n"
            "Suggested adjustments to improve your probability of success.")
    if sell_lines:
        text += "📉 Reduce:\n"
        text += "\n".join(sell_lines)
        text += "\n\n"
    if buy_lines:
        text += "📈 Increase:\n"
        text += "\n".join(buy_lines)
        text += "\n\n"
    text += (
        f"🎯 Goal Success\n"
        f"Current: {old_prob:.0f}%\n"
        f"Projected: {new_prob:.0f}%\n\n"
        f"🛡 Risk\n"
        f"{old_risk:.0f}% → {new_risk:.0f}%\n\n"
        f"💰 Suggested extra investing\n"
        f"+${best['monthly_boost']}/mo")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                    text="✅ Apply Goal Fix",
                    callback_data="confirm_goal_fix")]])
    print("PORTFOLIO VIEW:")
    print(metrics.get("goal_results"))
    print("GOAL FIX:")
    print(goal_analysis)
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
        preview["trades"],
        preview["prices_dict"])
    await callback.message.answer(
        "✅ Goal Fix Applied\n\n"
        f"🎯 Goal Success:\n"
        f"{preview['old_prob']:.0f}% → "
        f"{preview['new_prob']:.0f}%\n\n"
        f"🛡 Risk:\n"
        f"{preview['old_risk']:.0f}% → "
        f"{preview['new_risk']:.0f}%\n\n"
        f"💰 Suggested extra investing:\n"
        f"+${preview['monthly_boost']}/mo")
    diagnosis_cache.pop(portfolio_id, None)