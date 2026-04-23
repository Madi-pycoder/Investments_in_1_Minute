import numpy as np

TRADING_DAYS = 252


def simulate_goal_probability(
    positions_data,
    current_value,
    goal_amount,
    years,
    portfolio_volatility=0.15,
    expected_return=0.07,
    simulations=2000,
    monthly_contribution=0,
    contribution_growth=0.03
):
    if not positions_data or current_value <= 0:
        return None

    if portfolio_volatility is None:
        return None

    days = years * TRADING_DAYS

    mu = expected_return / TRADING_DAYS
    sigma = portfolio_volatility / np.sqrt(TRADING_DAYS)

    random_returns = np.random.normal(
        mu,
        sigma,
        (simulations, days)
    )

    growth = np.cumprod(1 + random_returns, axis=1)

    values = np.zeros_like(growth)
    values[:, 0] = current_value

    for t in range(1, days):
        values[:, t] = values[:, t - 1] * (1 + random_returns[:, t])

    monthly_step = 21
    current_contribution = monthly_contribution

    for t in range(1, days):
        values[:, t] = values[:, t - 1] * (1 + random_returns[:, t])

        if t % monthly_step == 0:
            values[:, t] += current_contribution
            current_contribution *= (1 + contribution_growth / 12)

    final_values = values[:, -1]

    prob = np.mean(final_values >= goal_amount) * 100

    if prob == 0:
        median = np.median(final_values)

        if median > goal_amount * 0.7:
            prob = 5.0

    return {
        "probability": round(float(np.mean(final_values >= goal_amount) * 100), 1),
        "expected": round(float(np.mean(final_values)), 2),
        "worst": round(float(np.percentile(final_values, 5)), 2)
    }


def calculate_monthly_contribution(current_value, goal, years, rate=0.07):
    months = years * 12
    r = rate / 12

    future_value_current = current_value * (1 + r) ** months
    needed = goal - future_value_current

    if needed <= 0:
        return 0

    monthly = needed / (((1 + r) ** months - 1) / r)
    return round(monthly, 2)


def analyze_goal(goal_result, monthly_needed, portfolio_volatility):
    if not goal_result:
        return None

    prob = goal_result["probability"]

    if prob >= 80:
        status = "🟢 Easy"
    elif prob >= 50:
        status = "🟡 Medium"
    else:
        status = "🔴 Hard"

    tips = []

    if prob < 50:
        tips.append("Increase monthly investment")
        tips.append("Extend time horizon")

    if prob == 0:
        tips.append("Goal likely unrealistic with current capital")

    if portfolio_volatility and portfolio_volatility > 0.2:
        tips.append("Reduce risk (portfolio too volatile)")

    return {
        "status": status,
        "monthly_needed": monthly_needed,
        "tips": tips,
    }


def optimize_multi_goals(goals_results):
    insights = []

    for r in goals_results:
        goal = r["goal"]
        prob = r["simulation"]["probability"]

        if prob < 50:
            insights.append(f"🚨 {goal['name']} at risk ({prob}%)")

    return insights



def simulate_multiple_goals(
    positions_data,
    total_value,
    goals,
    portfolio_volatility
):
    results = []

    for goal in goals:
        monthly = calculate_monthly_contribution(
            total_value,
            goal["amount"],
            goal["years"]
        )

        sim = simulate_goal_probability(
            positions_data,
            total_value,
            goal["amount"],
            goal["years"],
            portfolio_volatility=portfolio_volatility,
            monthly_contribution=monthly
        )

        analysis = analyze_goal(
            sim,
            monthly,
            portfolio_volatility
        )

        if sim is None:
            results.append({
                "goal": goal,
                "simulation": None,
                "analysis": None,
                "error": "NO_DATA"
            })
            continue

        results.append({
            "goal": goal,
            "simulation": sim,
            "analysis": analysis
        })

    return results



def allocate_capital_across_goals(goals):
    total_priority = sum(1 / max(g["priority"], 1) for g in goals)

    allocation = {}

    for g in goals:
        weight = (1 / g["priority"]) / total_priority
        allocation[g["name"]] = weight

    return allocation



def optimize_portfolio_for_goals(
    positions_data,
    total_value,
    goals,
    current_volatility
):
    if not goals or not positions_data:
        return None

    scenarios = []


    risk_levels = [0.10, 0.12, 0.15, 0.18]


    monthly_boosts = [0, 100, 300]

    for risk in risk_levels:
        for boost in monthly_boosts:

            goal_results = []

            for g in goals:
                monthly = calculate_monthly_contribution(
                    total_value,
                    g["amount"],
                    g["years"]
                ) + boost

                sim = simulate_goal_probability(
                    positions_data,
                    total_value,
                    g["amount"],
                    g["years"],
                    portfolio_volatility=risk,
                    monthly_contribution=monthly
                )

                if sim:
                    goal_results.append(sim["probability"])
                else:
                    goal_results.append(0)


            score = np.mean(goal_results)

            scenarios.append({
                "risk": risk,
                "monthly_boost": boost,
                "score": round(score, 1)
            })

    best = sorted(scenarios, key=lambda x: x["score"], reverse=True)

    return best[:3]



def build_goal_based_weights(positions_data, goals, target_risk):
    if not positions_data:
        return None


    avg_years = sum(g["years"] for g in goals) / len(goals)

    weights = {}

    base_weight = 1 / len(positions_data)

    for p in positions_data:
        ticker = p["ticker"]

        w = base_weight

        if avg_years <= 3:
            w *= 0.7
        elif avg_years >= 7:
            w *= 1.3


        if target_risk <= 0.12:
            w *= 0.8
        elif target_risk >= 0.18:
            w *= 1.2

        weights[ticker] = w


    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    return weights



def generate_auto_invest_plan(
    positions_data,
    monthly_amount,
    target_weights
):
    if not positions_data or not target_weights:
        return None

    positive_diffs = []

    for p in positions_data:
        ticker = p["ticker"]
        current_weight = p.get("weight", 0)
        target_weight = target_weights.get(ticker, 0)

        diff = target_weight - current_weight

        if diff > 0:
            positive_diffs.append((ticker, diff))

    if not positive_diffs:
        return None

    total_diff = sum(d for _, d in positive_diffs)

    plan = []

    for ticker, diff in positive_diffs:
        allocation = monthly_amount * (diff / total_diff)

        if allocation > 1:
            plan.append({
                "ticker": ticker,
                "amount": round(allocation, 2)
            })

    return sorted(plan, key=lambda x: x["amount"], reverse=True)



def run_what_if_scenarios(
    positions_data,
    current_value,
    goal,
    base_volatility
):
    scenarios = []
    base_prob = None

    variations = [
        {"name": "Base", "boost": 0, "years": 0},
        {"name": "+$200/mo", "boost": 200, "years": 0},
        {"name": "+2 years", "boost": 0, "years": 2},
        {"name": "Lower risk", "boost": 0, "risk": 0.12},
    ]

    for v in variations:
        monthly = calculate_monthly_contribution(
            current_value,
            goal["amount"],
            goal["years"] + v.get("years", 0)
        ) + v.get("boost", 0)


        sim = simulate_goal_probability(
        positions_data=positions_data,
        current_value=current_value,
        goal_amount=goal["amount"],
        years=goal["years"] + v.get("years", 0),
        portfolio_volatility=v.get("risk", base_volatility),
        monthly_contribution=monthly
        )

        if v["name"] == "Base":
            base_prob = sim["probability"]

        if base_prob is None:
            delta = 0
        else:
            delta = sim["probability"] - base_prob

        scenarios.append({
            "scenario": v["name"],
            "probability": sim["probability"],
            "delta": round(delta, 1)
        })

    return scenarios


def generate_smart_nudges(goal_results):
    nudges = []

    for r in goal_results:
        goal = r["goal"]
        sim = r["simulation"]

        if not sim:
            continue

        prob = sim["probability"]

        if prob < 40:
            nudges.append({
                "type": "critical",
                "text": f"{goal['name']}: +$100/mo → big improvement"
            })

        elif prob < 70:
            nudges.append({
                "type": "improve",
                "text": f"{goal['name']}: small boost needed"
            })

        else:
            nudges.append({
                "type": "good",
                "text": f"{goal['name']} on track"
            })

    return nudges
