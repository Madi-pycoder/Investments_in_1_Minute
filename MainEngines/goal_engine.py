import numpy as np
import logging
import inspect
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    force=True
)
TRADING_DAYS = 252

def simulate_goal_probability(
    positions_data, current_value,
    goal_amount, years,
    portfolio_volatility=0.15,
    expected_return=0.07,
    simulations=450,
    monthly_contribution=0,
    contribution_growth=0.03):
    if not positions_data or current_value <= 0:
        return None
    if portfolio_volatility is None:
        return None
    rng = np.random.default_rng()
    days = years * TRADING_DAYS
    mu = expected_return / TRADING_DAYS
    sigma = portfolio_volatility / np.sqrt(TRADING_DAYS)
    random_returns = rng.normal(mu, sigma, (simulations, days))
    values = np.zeros((simulations, days))
    values[:, 0] = current_value
    monthly_step = 21
    contribution = monthly_contribution
    for t in range(1, days):
        values[:, t] = values[:, t - 1] * (1 + random_returns[:, t])
        if t % monthly_step == 0:
            values[:, t] += contribution
            contribution *= (1 + contribution_growth / 12)
    final_values = values[:, -1]

    final_values = final_values[
        np.isfinite(final_values)
    ]

    if len(final_values) == 0:
        return {
            "probability": 0,
            "expected": 0,
            "worst": 0}
    logging.info(
        f"nan={np.isnan(final_values).sum()} "
        f"inf={np.isinf(final_values).sum()} "
        f"max={np.nanmax(final_values)}")
    prob = np.mean(final_values >= goal_amount) * 100
    if prob == 0:
        median = np.median(final_values)
        if median > goal_amount * 0.7:
            prob = 5.0
    return {
        "probability": round(float(prob), 1),
        "expected": round(float(np.mean(final_values)), 2),
        "worst": round(float(np.percentile(final_values, 5)), 2)}


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
        status = "🟢 Высокие шансы"
    elif prob >= 50:
        status = "🟡 Есть над чем поработать"
    else:
        status = "🔴 Цель под угрозой"
    tips = []
    if prob < 50:
        tips.append("Увеличить ежемесячные инвестиции")
        tips.append("Продлить срок достижения цели")
    if prob == 0:
        tips.append("Текущего капитала может быть недостаточно для этой цели")
    if portfolio_volatility and portfolio_volatility > 0.2:
        tips.append("Снизить риск портфеля")
    return {
        "status": status,
        "monthly_needed": monthly_needed,
        "tips": tips,}


def optimize_multi_goals(goal_results):
    insights = []
    for r in goal_results:
        goal = r["goal"]
        prob = r["simulation"]["probability"]
        if prob < 50:
            insights.append(f"🚨Цель '{goal['name']}' требует внимания ({prob}%)")
    return insights


def simulate_multiple_goals(positions_data, total_value, goals,
    portfolio_volatility, monthly_contribution):
    results = []
    auto_monthly = monthly_contribution
    for goal in goals:
        monthly = auto_monthly
        sim = simulate_goal_probability(
            positions_data,
            total_value,
            goal["amount"],
            goal["years"],
            portfolio_volatility=portfolio_volatility,
            monthly_contribution=monthly)
        required_monthly = calculate_monthly_contribution(
            total_value, goal["amount"], goal["years"], rate=0.07)
        actual_monthly = auto_monthly
        analysis = {
            "monthly_needed": required_monthly,
            "actual_monthly": actual_monthly}
        if sim is None:
            results.append({
                "goal": goal,
                "simulation": None,
                "analysis": None,
                "error": "NO_DATA"})
            continue
        results.append({
            "goal": goal,
            "simulation": sim,
            "analysis": analysis})

    return results


def allocate_capital_across_goals(goals):
    total_priority = sum(1 / max(g["priority"], 1) for g in goals)
    allocation = {}
    for g in goals:
        weight = (1 / g["priority"]) / total_priority
        allocation[g["name"]] = weight
    return allocation


def optimize_portfolio_for_goals(positions_data, total_value, goals):
    if not goals or not positions_data:
        return None
    scenarios = []
    risk_levels = np.arange(0.10, 0.26, 0.02)
    monthly_boosts = [
        0, 50, 100,
        150, 200,
        300, 400]
    for risk in risk_levels:
        for boost in monthly_boosts:
            probabilities = []
            for g in goals:
                monthly = (calculate_monthly_contribution(
                        total_value, g["amount"],
                        g["years"]) + boost)
                sim = simulate_goal_probability(
                    positions_data, total_value,
                    g["amount"], g["years"],
                    portfolio_volatility=risk,
                    expected_return=0.04 + risk * 0.25,
                    monthly_contribution=monthly)
                prob = sim["probability"] if sim else 0
                probabilities.append(prob)
            avg_probability = np.mean(probabilities)
            penalty = 0
            penalty += max(0, (risk - 0.18) * 120)
            penalty += boost * 0.03
            final_score = avg_probability - penalty
            scenarios.append({
                "risk": round(risk, 2),
                "monthly_boost": boost,
                "score": round(final_score, 1),
                "raw_probability": round(avg_probability, 1)})
    best = sorted(
        scenarios, key=lambda x: x["score"], reverse=True)
    return best[:5]


def build_goal_based_weights(positions_data, goals, target_risk,):
    if not positions_data:
        return {}
    weights = {}
    avg_years = (
        sum(g["years"] for g in goals) / len(goals)
        if goals else 5)
    for p in positions_data:
        ticker = p["ticker"]
        current = p.get("weight", 0)
        score = 1.0
        if avg_years >= 10:
            score *= 1.45
        elif avg_years >= 7:
            score *= 1.25
        elif avg_years <= 3:
            score *= 0.85

        if current > 0.45:
            score *= 0.55
        elif current > 0.35:
            score *= 0.75
        elif current > 0.25:
            score *= 0.90

        if current < 0.05:
            score *= 2.2
        elif current < 0.10:
            score *= 1.6

        if ticker in ["SPUS", "HLAL"]:
            if target_risk <= 0.14:
                score *= 1.7
            else:
                score *= 1.15
        if ticker in ["NVDA", "TSM", "AMD"]:
            if target_risk >= 0.18:
                score *= 1.6
            else:
                score *= 0.8
        weights[ticker] = max(score, 0.05)
    total = sum(weights.values())
    return {
        t: w / total
        for t, w in weights.items()}

def compute_smart_diffs(positions, target_weights):
    diffs = []
    for p in positions:
        ticker = p["ticker"]
        current = p.get("weight", 0)
        target = target_weights.get(ticker, 0)
        diff = target - current
        if current > 0.25:
            diff *= 0.5
        if current > 0.45:
            diff *= 0.1
        if current < target:
            diff *= 1.2
        if abs(diff) > 0.002:
            diffs.append((ticker, diff))
    return diffs


def generate_auto_invest_plan(positions_data,
    monthly_amount, target_weights,
    max_single_weight=0.40):
    if not positions_data or monthly_amount <= 0:
        return []
    core_budget = monthly_amount * 0.75
    maintenance_budget = monthly_amount * 0.25
    scored = []
    for p in positions_data:
        ticker = p["ticker"]
        current = p.get("weight", 0)
        target = target_weights.get(ticker, 0)
        gap = max(target - current, 0)
        score = target * 0.35 + gap * 0.65
        if current > max_single_weight:
            score *= 0.25
        if current < target * 0.6:
            score *= 1.25
        scored.append((ticker, score, target))
    if not scored:
        return []
    total_score = sum(x[1] for x in scored)
    plan = []
    for ticker, score, target in scored:
        allocation = (core_budget * (score / total_score))
        allocation += maintenance_budget * target
        if allocation < 5:
            continue
        plan.append({
            "ticker": ticker, "amount": round(allocation, 2)})
    allocated = sum(x["amount"] for x in plan)
    diff = round(monthly_amount - allocated, 2)
    if plan and abs(diff) > 0:
        plan[0]["amount"] += diff
    return sorted(plan, key=lambda x: x["amount"], reverse=True)


def run_what_if_scenarios(positions_data, portfolio_total, goal, base_volatility,
    monthly_budget):
    logging.info(
        f"WHAT_IF monthly_budget={monthly_budget}")
    logging.info(
        f"CALLER={inspect.stack()[1].filename}:"
        f"{inspect.stack()[1].lineno}")
    scenarios = []
    base_prob = None
    variations = [
        {"name": "Текущий план", "boost": 0, "years": 0},
        {"name": f"+${int(monthly_budget)}/мес", "boost": monthly_budget, "years": 0},
        {"name": "+2 года к сроку", "boost": 0, "years": 2},
        {"name": "Более консервативный портфель", "boost": 0, "risk": 0.12},]
    logging.info(f"WHAT_IF monthly_budget={monthly_budget}")
    for v in variations:
        base_monthly = monthly_budget
        monthly = base_monthly + v.get("boost", 0)
        sim = simulate_goal_probability(
        positions_data=positions_data,
        current_value=portfolio_total,
        goal_amount=goal["amount"],
        years=goal["years"] + v.get("years", 0),
        portfolio_volatility=v.get("risk", base_volatility),
        monthly_contribution=monthly)
        if base_prob is None:
            base_prob = sim["probability"]
        if sim is None:
            continue
        if base_prob is None:
            delta = 0
        else:
            delta = sim["probability"] - base_prob
        scenarios.append({
            "scenario": v["name"],
            "probability": sim["probability"],
            "delta": round(delta, 1)})
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
                "text": f"{goal['name']}: +$100/мес заметно повысит шансы"})
        elif prob < 70:
            needed = r["analysis"]["monthly_needed"]
            if needed <= 0:
                nudges.append({
                    "type": "good",
                    "text": f"{goal['name']} достижим, если следовать плану"})
            else:
                nudges.append({
                    "type": "improve",
                    "text": f"Для цели '{goal['name']}' может потребоваться ещё ~ ${int(needed)}/мес"})
        else:
            nudges.append({
                "type": "good",
                "text": f"Цель '{goal['name']}' движется по плану"})
    return nudges


def calculate_goal_score(probability, years_left):
    score = probability
    if years_left <= 2:
        score = score * 0.9
    return min(round(score), 100)


def get_goal_levels(prob):
    if prob >= 85:
        return "🏆 Отличный прогресс"
    if prob >= 70:
        return "🚀 Хорошие шансы"
    if prob >= 50:
        return "📈 Умеренные шансы"
    if prob >= 25:
        return "⚠️ Требуются улучшения"
    return "🚨 Высокий риск не достичь цель"


def get_next_milestones(current_value, goal_amount):
    milestones = [0.25, 0.5, 0.75, 1.0]
    for m in milestones:
        target = goal_amount * m
        if current_value < target:
            return {
                "percent": int(m*100),
                "amount": round(target, 2)}
    return {
        "percent": 100,
        "amount": goal_amount}


def build_goal_insight(goal_result):
    prob = goal_result["simulation"]["probability"]
    monthly = goal_result["analysis"]["monthly_needed"]
    if prob >= 80:
        return "Цель движется по плану"
    if monthly <= 0:
        return "Стоит увеличить срок достижения цели"
    return f"+${int(monthly)}/мес могут существенно повысить шансы на успех"
