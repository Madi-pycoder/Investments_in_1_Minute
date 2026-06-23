import asyncio
from MainMetricsComputingFeatures.riskmanagement import calculate_portfolio_risk, generate_risk_alerts
from MainEngines.shariah_optimizer import optimize_shariah_portfolio
from MainEngines.sharpe_optimizer import optimize_by_sharpe
from MainEngines.halal_portfolio_generator import generate_halal_portfolio
from MainEngines.portoflio_rebalance import calculate_rebalance
from MainMetricsComputingFeatures.shariah import calculate_portfolio_purification, shariah_screen
from Explanation.ai_explain import explain_portfolio_logic
from MainEngines.goal_engine import (
    build_goal_based_weights,
    simulate_multiple_goals, generate_auto_invest_plan,
    run_what_if_scenarios, generate_smart_nudges,)
from MarketFeatures.market_regime import detect_market_regime
from ProfileData.user_profile import get_effective_monthly_budget, get_portfolio_profile
from ProjectDataBase.market_data_service import get_price_history, update_history
import numpy as np

async def get_market_prices():
    hist = await get_price_history("SPY")
    if len(hist) < 30:
        await update_history("SPY")
        hist = await get_price_history("SPY")
    if not hist:
        return None
    closes = [
        h.close
        for h in hist
        if h.close is not None]
    if len(closes) < 30:
        return None
    return np.array(closes)


def build_positions_data(positions, prices, data):
    positions_data = []
    total_value = 0
    stocks = data["stocks_batch"]
    for p in positions:
        price = (prices or {}).get(p.ticker)
        stock = stocks.get(p.ticker, {})
        if price is None:
            price = p.average_price or 1
        value = p.quantity * price
        total_value += value
        positions_data.append({
            "ticker": p.ticker,
            "value": value,
            "quantity": p.quantity,
            "avg_price": p.average_price,
            "asset_type": stock.get("quoteType"),
            "price": price})
    for p in positions_data:
        p["weight"] = p["value"] / total_value if total_value else 0
    for p in positions_data:
        avg = p.get("avg_price", 0)
        current = p.get("price", 0)
        if avg:
            pnl_pct = ((current - avg) / avg) * 100
            pnl_abs = (current - avg) * p["quantity"]
        else:
            pnl_pct = 0
            pnl_abs = 0
        p["pnl_pct"] = pnl_pct
        p["pnl_abs"] = pnl_abs
    print("BUILD POSITIONS")
    print([p.ticker for p in positions])
    return positions_data, total_value




def get_top_movers(positions_data):
    sorted_positions = sorted(positions_data,
        key=lambda x: x.get("pnl_pct", 0), reverse=True)
    return sorted_positions[:3], sorted_positions[-3:]



async def compute_async_insights(positions_data, stocks):
    tickers = [p["ticker"] for p in positions_data]
    risk_task = asyncio.create_task(calculate_portfolio_risk(positions_data))
    sharpe_task = asyncio.create_task(optimize_by_sharpe(tickers[:5]))
    halal_task = asyncio.create_task(generate_halal_portfolio(tickers[:5], stocks))
    risk_raw, sharpe, halal = await asyncio.gather(risk_task, sharpe_task,
        halal_task, return_exceptions=True)
    if isinstance(risk_raw, Exception) or not risk_raw:
        risk = {
            "volatility": 0,
            "diversification": 0,
            "concentration": "UNKNOWN",
            "risk_score": 0}
    else:
        risk = {
            "volatility": risk_raw.get("volatility") or 0,
            "diversification": risk_raw.get("diversification") or 0,
            "concentration": risk_raw.get("concentration") or "UNKNOWN",
            "risk_score": risk_raw.get("risk_score") or 0}
    return risk, sharpe, halal




def compute_sector_exposure(positions, prices, stocks, total_value):
    sector_exposure = {}
    for p in positions:
        sector = stocks.get(p.ticker, {}).get("sector", "Other")
        value = p.quantity * prices.get(p.ticker, 0)
        sector_exposure[sector] = sector_exposure.get(sector, 0) + value
    if total_value:
        sector_exposure = {k: v / total_value for k, v in sector_exposure.items()}
    top_sector = max(sector_exposure, key=sector_exposure.get, default=None)
    top_weight = sector_exposure.get(top_sector, 0)
    return sector_exposure, top_sector, top_weight



def compute_goal_insights(positions_data, total_value, goals, risk, portfolio_profile):
    if not goals:
        return None, None, [], None
    vol = (risk.get("volatility") or 15) / 100
    goal_weights = build_goal_based_weights(positions_data, goals, vol)
    auto_invest = generate_auto_invest_plan(
        positions_data, monthly_amount=300, target_weights=goal_weights,)
    goal_results = simulate_multiple_goals(
        positions_data,
        total_value,
        goals,
        vol)
    monthly_budget = get_effective_monthly_budget(portfolio_profile, total_value)
    nudges = generate_smart_nudges(goal_results)
    what_if = None
    if goals:
        what_if = run_what_if_scenarios(positions_data,
            total_value, goals[0], vol, monthly_budget)
    return goal_results, auto_invest, nudges, what_if



def compute_sector_fast(positions, prices, stocks):
    sector = {}
    total = 0
    for p in positions:
        val = p.quantity * prices.get(p.ticker, 0)
        if val == 0:
            continue
        total += val
        stock_info = stocks.get(p.ticker, {}) or {}
        s = (
            stock_info.get("sector")
            or stock_info.get("industry")
            or ("ETF" if stock_info.get("quoteType") == "ETF" else None)
            or "Other")
        sector[s] = sector.get(s, 0) + val
    if total:
        sector = {k: v / total for k, v in sector.items()}
    return sector

async def compute_light_metrics(data):
    positions = data["positions"]
    prices = data["prices_dict"]
    stocks = data["stocks_batch"]
    positions_data, total_value = build_positions_data(positions, prices, data)
    for p in positions_data:
        stock = stocks.get(p["ticker"])
        if not stock:
            p["shariah_compliant"] = None
            continue
        screening = await shariah_screen(stock)
        p["shariah_compliant"] = (
                screening["status"] == "СООТВЕТСТВУЕТ ШАРИАТУ ✅")
    sector_exposure = compute_sector_fast(positions, prices, stocks)
    goal_results = simulate_multiple_goals(
        positions_data,
        total_value,
        data.get("goals", []), 0.15)
    return {
        "positions_data": positions_data,
        "total_value": total_value,
        "sector_exposure": sector_exposure,
        "goal_results": goal_results}




async def compute_rebalance(positions_data, stocks, total_value):
    weights = await optimize_shariah_portfolio(positions_data, stocks)
    if not weights:
        return None
    return calculate_rebalance(positions_data, weights, total_value)




async def compute_portfolio_metrics(data):
    positions = data["positions"]
    portfolio_id = data.get("portfolio_id")
    prices = data["prices_dict"]
    stocks = data["stocks_batch"]
    goals = data.get("goals") or []
    portfolio_profile = await get_portfolio_profile(portfolio_id)
    positions_data, total_value = build_positions_data(positions, prices, data)
    for p in positions_data:
        stock = stocks.get(p["ticker"])
        if not stock:
            p["shariah_compliant"] = None
            continue
        screening = await shariah_screen(stock)
        p["shariah_compliant"] = (
            screening["status"] == "СООТВЕТСТВУЕТ ШАРИАТУ ✅")
    top_gainers, top_losers = get_top_movers(positions_data)
    risk, sharpe, halal = await compute_async_insights(positions_data, stocks)
    shariah_rebalance = await compute_rebalance(positions_data, stocks, total_value)
    sector_exposure, top_sector, top_weight = compute_sector_exposure(
        positions, prices, stocks, total_value)
    purification = await calculate_portfolio_purification(
        positions_data,
        stocks)
    goal_results, auto_invest, nudges, what_if = compute_goal_insights(
        positions_data, total_value,
        goals, risk, portfolio_profile)
    alerts = generate_risk_alerts(risk)
    goals = data.get("goals") or []
    market_prices = await get_market_prices()
    regime_data = detect_market_regime(market_prices)
    regime = regime_data["regime"]
    regime_score = regime_data["score"]
    explanation = explain_portfolio_logic(
        positions_data,
        risk,
        top_sector,
        top_weight)
    return {
        "positions_data": positions_data,
        "total_value": total_value,
        "risk": risk,
        "goals": goals,
        "goal_results": goal_results,
        "nudges": nudges,
        "sharpe": sharpe,
        "halal": halal,
        "shariah_rebalance": shariah_rebalance,
        "sector_exposure": sector_exposure,
        "top_sector": top_sector,
        "top_sector_weight": top_weight,
        "portfolio_volatility": risk["volatility"],
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "alerts": alerts,
        "explanation": explanation,
        "market_regime": regime,
        "regime_score": regime_score,
        "purification": purification}
