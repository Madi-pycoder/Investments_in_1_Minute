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
    generate_smart_nudges)



async def compute_portfolio_metrics(data, portfolio_id):
    positions = data["positions"]
    prices = data["prices_dict"]
    stocks = data["stocks_batch"]

    positions_data = []
    total_value = 0


    for p in positions:
        price = prices.get(p.ticker)
        if not price:
            continue

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


    sorted_positions = sorted(
        positions_data,
        key=lambda x: x.get("pnl_pct", 0),
        reverse=True
    )

    top_gainers = sorted_positions[:3]
    top_losers = sorted_positions[-3:]

    tickers = [p["ticker"] for p in positions_data]




    risk_task = asyncio.create_task(calculate_portfolio_risk(positions_data))
    fast_tickers = tickers[:5]
    sharpe_task = asyncio.create_task(optimize_by_sharpe(fast_tickers))
    halal_task = asyncio.create_task(generate_halal_portfolio(fast_tickers, stocks))

    results = await asyncio.gather(
        risk_task,
        sharpe_task,
        halal_task,
        return_exceptions=True
    )

    risk_raw, sharpe, halal = results

    # --- SAFE RISK ---
    if isinstance(risk_raw, Exception) or risk_raw is None:
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

    if risk is None:
        risk = {"volatility": 0, "risk_score": 0}

    shariah_weights = optimize_shariah_portfolio(positions_data, stocks)


    shariah_rebalance = None
    if shariah_weights:
        shariah_rebalance = calculate_rebalance(
            positions_data,
            shariah_weights,
            total_value
        )


    alerts = generate_risk_alerts(risk)

    goals = data.get("goals") or []


    sector_weights = {}
    for p in positions:
        sector = stocks.get(p.ticker, {}).get("sector")
        if sector:
            sector_weights[sector] = sector_weights.get(sector, 0) + (p.quantity * prices.get(p.ticker, 0))

    if total_value:
        sector_weights = {k: v / total_value for k, v in sector_weights.items()}


    sector_exposure = {}

    for p in positions:
        sector = stocks.get(p.ticker, {}).get("sector", "Other")
        value = p.quantity * prices.get(p.ticker, 0)

        sector_exposure[sector] = sector_exposure.get(sector, 0) + value

    if total_value:
        sector_exposure = {
            k: v / total_value for k, v in sector_exposure.items()
        }


    top_sector = None
    top_weight = 0

    for s, w in sector_exposure.items():
        if w > top_weight:
            top_sector = s
            top_weight = w

    goal_weights = build_goal_based_weights(
        positions_data,
        goals,
        risk["volatility"] / 100 if risk else 0.15
    )

    auto_invest = generate_auto_invest_plan(
        positions_data,
        monthly_amount=300,
        target_weights=goal_weights
    )

    goal_results = simulate_multiple_goals(
        positions_data,
        total_value,
        goals,
        risk["volatility"] / 100 if risk else 0.15
    )

    nudges = generate_smart_nudges(goal_results)

    what_if = None
    if goals:
        what_if = run_what_if_scenarios(
            positions_data,
            total_value,
            goals[0],
            risk["volatility"] / 100 if risk else 0.15
        )

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
        "monte_carlo": None,
        "goals": goals,
        "goal_results": goal_results,
        "sharpe": sharpe,
        "halal": halal,
        "shariah_rebalance": shariah_rebalance,
        "sector_weights": sector_weights,
        "sector_exposure": sector_exposure,
        "top_sector": top_sector,
        "top_sector_weight": top_weight,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "alerts": alerts,
        "worst_case": None,
        "auto_invest": auto_invest,
        "what_if": what_if,
        "nudges": nudges,
    }