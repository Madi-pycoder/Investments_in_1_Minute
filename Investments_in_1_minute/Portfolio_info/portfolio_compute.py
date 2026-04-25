import asyncio
from riskmanagement import calculate_portfolio_risk, generate_risk_alerts
from shariah_optimizer import optimize_shariah_portfolio
from sharpe_optimizer import optimize_by_sharpe
from halal_portfolio_generator import generate_halal_portfolio
from portoflio_rebalance import calculate_rebalance
from ai_explain import explain_portfolio_logic
from goal_engine import (
    build_goal_based_weights,
    simulate_multiple_goals,
    generate_auto_invest_plan,
    run_what_if_scenarios,
    generate_smart_nudges,
)
from market_regime import detect_market_regime
import yfinance as yf

async def get_market_prices():
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="1y")

        if hist is None or hist.empty:
            return None

        return hist["Close"].values

    except:
        return None


def build_positions_data(positions, prices):
    positions_data = []
    total_value = 0

    for p in positions:
        price = prices.get(p.ticker)
        if not price:
            price = p.average_price or 1

        value = p.quantity * price
        total_value += value

        positions_data.append({
            "ticker": p.ticker,
            "value": value,
            "quantity": p.quantity,
            "avg_price": p.average_price,
            "price": price
        })

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

    return positions_data, total_value




def get_top_movers(positions_data):
    sorted_positions = sorted(
        positions_data,
        key=lambda x: x.get("pnl_pct", 0),
        reverse=True
    )

    return sorted_positions[:3], sorted_positions[-3:]



async def compute_async_insights(positions_data, stocks):
    tickers = [p["ticker"] for p in positions_data]

    risk_task = asyncio.create_task(calculate_portfolio_risk(positions_data))
    sharpe_task = asyncio.create_task(optimize_by_sharpe(tickers[:5]))
    halal_task = asyncio.create_task(generate_halal_portfolio(tickers[:5], stocks))

    risk_raw, sharpe, halal = await asyncio.gather(
        risk_task,
        sharpe_task,
        halal_task,
        return_exceptions=True
    )

    if isinstance(risk_raw, Exception) or not risk_raw:
        risk = {
            "volatility": 0,
            "diversification": 0,
            "concentration": "UNKNOWN",
            "risk_score": 0
        }
    else:
        risk = {
            "volatility": risk_raw.get("volatility") or 0,
            "diversification": risk_raw.get("diversification") or 0,
            "concentration": risk_raw.get("concentration") or "UNKNOWN",
            "risk_score": risk_raw.get("risk_score") or 0
        }

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



def compute_goal_insights(positions_data, total_value, goals, risk):
    vol = (risk.get("volatility") or 15) / 100

    goal_weights = build_goal_based_weights(positions_data, goals, vol)

    auto_invest = generate_auto_invest_plan(
        positions_data,
        monthly_amount=300,
        target_weights=goal_weights
    )

    goal_results = simulate_multiple_goals(
        positions_data,
        total_value,
        goals,
        vol
    )

    nudges = generate_smart_nudges(goal_results)

    what_if = None
    if goals:
        what_if = run_what_if_scenarios(
            positions_data,
            total_value,
            goals[0],
            vol
        )
    return goal_results, auto_invest, nudges, what_if




def compute_rebalance(positions_data, stocks, total_value):
    weights = optimize_shariah_portfolio(positions_data, stocks)

    if not weights:
        return None

    return calculate_rebalance(positions_data, weights, total_value)




async def compute_portfolio_metrics(data, portfolio_id):
    positions = data["positions"]
    prices = data["prices_dict"]
    stocks = data["stocks_batch"]
    goals = data.get("goals") or []


    positions_data, total_value = build_positions_data(positions, prices)
    top_gainers, top_losers = get_top_movers(positions_data)
    risk, sharpe, halal = await compute_async_insights(positions_data, stocks)
    shariah_rebalance = compute_rebalance(positions_data, stocks, total_value)
    sector_exposure, top_sector, top_weight = compute_sector_exposure(
        positions, prices, stocks, total_value
    )

    goal_results, auto_invest, nudges, what_if = compute_goal_insights(
        positions_data,
        total_value,
        goals,
        risk
    )

    alerts = generate_risk_alerts(risk)
    goals = data.get("goals") or []
    market_prices = await get_market_prices()
    regime = detect_market_regime(market_prices)

    explanation = explain_portfolio_logic(
        positions_data,
        risk,
        None,
        None,
        None,
        top_sector,
        top_weight
    )

    return {
        "positions_data": positions_data,
        "total_value": total_value,
        "risk": risk,
        "goals": goals,
        "goal_results": goal_results,
        "sharpe": sharpe,
        "halal": halal,
        "shariah_rebalance": shariah_rebalance,
        "sector_exposure": sector_exposure,
        "top_sector": top_sector,
        "top_sector_weight": top_weight,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "alerts": alerts,
        "explanation": explanation,
        "market_regime": regime
    }
