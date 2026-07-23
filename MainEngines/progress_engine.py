from datetime import datetime, timezone

def build_goal_progress(goal_results, portfolio_value):
    results = []
    now = datetime.now(timezone.utc)
    for item in goal_results:
        goal = item["goal"]
        target = goal["amount"]
        years = goal["years"]
        current = portfolio_value
        progress_now = min(current / target, 1)
        excepted = 1 / years
        behind = max(0, excepted - progress_now)
        if behind < 0.05:
            status = "В пути"
        elif behind < 0.15:
            status = "Есть риск не достчиь цели"
        else:
            status = "Критично"
        results.append({
            "goal": goal["name"],
            "progress_now": progress_now,
            "progress_excepted": excepted,
            "behind": behind,
            "status": status})
    return results