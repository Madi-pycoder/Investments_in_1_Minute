from user_profile import (
    get_effective_monthly_budget,
    get_risk_multiplier
)
from goal_engine import (
    build_goal_based_weights,
    generate_auto_invest_plan,
    simulate_multiple_goals,
    optimize_portfolio_for_goals,
    run_what_if_scenarios,
    generate_smart_nudges
)
from market_regime import apply_market_regime_shift

class RoboAdvisor:

    def __init__(self, profile, metrics):
        self.profile = profile
        self.metrics = metrics

        self.positions = metrics.get("positions_data", [])
        self.total_value = metrics.get("total_value", 0)
        self.goals = metrics.get("goals", [])
        self.risk = metrics.get("risk", {})
        self.regime = metrics.get("market_regime", "unknown")

    def get_issues(self):
        issues = []

        monthly_budget = get_effective_monthly_budget(self.profile)

        if monthly_budget <= 0:
            issues.append("Set monthly budget")

        if not self.positions:
            issues.append("No positions")

        if not self.goals:
            issues.append("No goals set")

        return issues


    def build_auto_invest_plan(self):

        if not self.positions:
            return None

        monthly_budget = get_effective_monthly_budget(
            self.profile,
            self.total_value
        )

        if monthly_budget <= 0:
            return None

        base_vol = (self.risk.get("volatility") or 15) / 100

        risk_multiplier = get_risk_multiplier(self.profile)
        adjusted_vol = base_vol * risk_multiplier

        if self.goals:
            optimizations = optimize_portfolio_for_goals(
                self.positions,
                self.total_value,
                self.goals,
                adjusted_vol
            )

            if optimizations:
                best = optimizations[0]
                target_risk = best["risk"]
            else:
                target_risk = adjusted_vol
        else:
            target_risk = adjusted_vol

        target_weights = build_goal_based_weights(
            self.positions,
            self.goals,
            target_risk
        )
        target_weights = apply_market_regime_shift(
            target_weights,
            self.regime
        )
        plan = generate_auto_invest_plan(
            self.positions,
            monthly_budget,
            target_weights
        )

        if self.regime == "crisis":
            target_risk *= 0.7

        elif self.regime == "bull":
            target_risk *= 1.1

        return plan


    def analyze_goals(self):

        if not self.goals:
            return None

        vol = (self.risk.get("volatility") or 15) / 100

        return simulate_multiple_goals(
            self.positions,
            self.total_value,
            self.goals,
            vol
        )


    def optimize_portfolio(self):

        if not self.goals:
            return None

        vol = (self.risk.get("volatility") or 15) / 100

        return optimize_portfolio_for_goals(
            self.positions,
            self.total_value,
            self.goals,
            vol
        )


    def generate_actions(self):

        actions = []

        plan = self.build_auto_invest_plan()

        if not plan:
            actions.append({
                "type": "warning",
                "text": "Set or increase monthly budget"
            })
        else:
            total = sum(x["amount"] for x in plan)

            if total < 50:
                actions.append({
                    "type": "improve",
                    "text": "Increase monthly investment"
                })

        goal_analysis = self.analyze_goals()

        if goal_analysis:
            for g in goal_analysis:
                prob = g["simulation"]["probability"]

                if prob < 40:
                    actions.append({
                        "type": "critical",
                        "text": f"{g['goal']['name']} is at risk"
                    })

        return actions

    def run_what_if(self):

        if not self.goals:
            return None

        vol = (self.risk.get("volatility") or 15) / 100

        return run_what_if_scenarios(
            self.positions,
            self.total_value,
            self.goals[0],
            vol
        )

    def get_nudges(self):

        goal_analysis = self.analyze_goals()

        if not goal_analysis:
            return None

        return generate_smart_nudges(goal_analysis)
