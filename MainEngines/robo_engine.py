from ProfileData.user_profile import (
    get_effective_monthly_budget,
    get_risk_multiplier)
from MainEngines.goal_engine import (
    build_goal_based_weights,
    generate_auto_invest_plan,
    simulate_multiple_goals,
    optimize_portfolio_for_goals,
    run_what_if_scenarios,
    generate_smart_nudges)
from MarketFeatures.market_regime import apply_market_regime_shift

class RoboAdvisor:
    def __init__(self, user_profile, portfolio_profile, metrics, data):
        self.user_profile = user_profile
        self.portfolio_profile = portfolio_profile
        self.metrics = metrics
        self.positions = metrics.get("positions_data", [])
        self.total_value = metrics.get("total_value", 0)
        self.goals = data["goals"]
        self.risk = metrics.get("risk", {})
        self.regime = metrics.get("market_regime", "unknown")
        self._cached_plan = None
        self._cached_goal_analysis = None
        self._cached_nudges = None

    def get_issues(self):
        issues = []
        monthly_budget = get_effective_monthly_budget(
            self.portfolio_profile,
            self.total_value)
        if monthly_budget <= 0:
            issues.append("Set monthly budget (currently auto-estimated)")
        if not self.positions:
            issues.append("No positions")
        if not self.goals:
            issues.append("No goals set")
        return issues

    def build_auto_invest_plan(self):
        if self._cached_plan is not None:
            return self._cached_plan
        if not self.positions:
            return {
                "ok": False,
                "status": "no_positions",
                "plan": [],
                "reason": "Portfolio has no positions"}
        monthly_budget = (get_effective_monthly_budget(
            self.portfolio_profile,
            self.total_value))
        if monthly_budget <= 0:
            return {
                "ok": False,
                "status": "no_budget",
                "plan": [],
                "reason": "Monthly budget is not configured"}
        base_vol = (self.risk.get("volatility") or 15) / 100
        risk_multiplier = get_risk_multiplier(self.portfolio_profile)
        adjusted_vol = base_vol * risk_multiplier
        target_risk = adjusted_vol
        if self.goals:
            optimizations = optimize_portfolio_for_goals(
                self.positions,
                self.total_value,
                self.goals,)
            if optimizations:
                target_risk = optimizations[0]["risk"]
        target_weights = build_goal_based_weights(
            self.positions,
            self.goals,
            target_risk)
        if not target_weights:
            target_weights = {
                p["ticker"]: 1 / len(self.positions)
                for p in self.positions}
        target_weights = apply_market_regime_shift(target_weights, self.regime)
        plan = generate_auto_invest_plan(
            self.positions,
            monthly_budget,
            target_weights,)
        if not plan:
            return {
                "ok": False,
                "status": "empty_plan",
                "plan": [],
                "reason": "No investment allocations generated"}
        self._cached_plan = {
            "ok": True,
            "status": "ready",
            "plan": plan,
            "reason": None}
        return self._cached_plan

    def analyze_goals(self):
        if self._cached_goal_analysis is not None:
            return self._cached_goal_analysis
        if not self.goals:
            return None
        vol = (self.risk.get("volatility") or 15) / 100
        self._cached_goal_analysis = simulate_multiple_goals(
            self.positions,
            self.total_value,
            self.goals, vol)
        return self._cached_goal_analysis

    def generate_actions(self):
        actions = []
        result = self.build_auto_invest_plan()
        plan = result["plan"]
        if not result["ok"]:
            actions.append({
                "type": "warning",
                "text": "Set or increase monthly budget"})
        else:
            total = sum(x["amount"] for x in plan)
            if total < 50:
                actions.append({
                    "type": "improve",
                    "text": "Increase monthly investment"})
        goal_analysis = self.analyze_goals()
        if goal_analysis:
            for g in goal_analysis:
                prob = g["simulation"]["probability"]
                if prob < 40:
                    actions.append({
                        "type": "critical",
                        "text": f"{g['goal']['name']} is at risk"})
        return actions

    def run_what_if(self):
        if not self.goals:
            return None
        vol = (self.risk.get("volatility") or 15) / 100
        return run_what_if_scenarios(
            self.positions,
            self.total_value,
            self.goals[0], vol)

    def get_nudges(self):
        if self._cached_nudges is not None:
            return self._cached_nudges
        goal_analysis = self.analyze_goals()
        if not goal_analysis:
            return []
        self._cached_nudges = generate_smart_nudges(goal_analysis)
        return self._cached_nudges