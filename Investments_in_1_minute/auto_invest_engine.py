from datetime import datetime
from user_profile import get_user_profile, update_user_profile
from robo_engine import RoboAdvisor
from Portfolio_info.portfolio_data import load_portfolio_data
import requets as rq


async def run_auto_invest_for_user(user_id, portfolio_id):

    profile = get_user_profile(user_id)

    if not profile or not profile.auto_invest_enabled:
        return {"status": "skipped(enable auto-invest first)"}

    data = await load_portfolio_data(portfolio_id)

    if not data["positions"]:
        return {"status": "no_positions"}

    from Portfolio_info.portfolio_compute import compute_portfolio_metrics
    metrics = await compute_portfolio_metrics(data, portfolio_id)

    robo = RoboAdvisor(profile, metrics)

    plan = robo.build_auto_invest_plan()

    if not plan:
        return {"status": "no_plan"}

    trades = []

    for item in plan:
        trades.append({
            "ticker": item["ticker"],
            "amount": item["amount"],
            "action": "BUY"
        })

    await rq.execute_rebalance(
        portfolio_id,
        trades,
        data["prices_dict"]
    )

    update_user_profile(
        user_id,
        last_auto_invest=datetime.utcnow().isoformat()
    )

    return {
        "status": "executed",
        "trades": trades
    }