import uuid
from financial_models import InsightCard
from MainEngines.goal_engine import optimize_portfolio_for_goals
from VisualFeatures.renderer import classify_goal_gap


class FinancialBrain:
    MAX_INSIGHTS = 3
    def __init__(self, robo):
        self.robo = robo
        self.user_profile = robo.user_profile
        self.portfolio_profile = robo.portfolio_profile
        self.metrics = robo.metrics
        self.positions = robo.positions or []
        self.goals = robo.goals or []
        self.risk = robo.risk or {}
        self.regime = robo.regime

    def generate(self):
        insights = []
        insights.extend(self.goal_insights())
        insights.extend(self.risk_insights())
        insights.extend(self.diversification_insights())
        insights.extend(self.market_insights())
        insights.extend(self.behavior_insights())
        insights.sort(key=lambda x: x.priority, reverse=True)
        print("GOALS:", self.goals)
        return insights[:self.MAX_INSIGHTS]



    def goal_insights(self):
        items = []
        results = self.robo.analyze_goals()
        if not results:
            return items
        positions_data = self.metrics.get("positions_data", [])
        total_value = self.metrics.get("total_value", 0)
        goals = self.goals
        optimizations = optimize_portfolio_for_goals(positions_data, total_value, goals)
        if not optimizations:
            return items
        current_budget = (self.portfolio_profile.monthly_budget or 0)
        for r in results:
            sim = r.get("simulation") or {}
            analysis = r.get("analysis") or {}
            goal = r.get("goal") or {}
            probability = sim.get("probability", 0)
            if probability >= 75:
                continue
            goal_name = (
                goal.get("name", "Goal")
                .replace("_", " ")
                .title())
            years = goal.get("years", "?")
            monthly_needed = (analysis.get("monthly_needed", 0))
            delta = max(0, monthly_needed - current_budget)
            severity = (
                "critical"
                if probability < 40
                else "high")
            gap_type = classify_goal_gap(delta)
            if gap_type == "manageable":
                headline = f"{goal_name} needs +${int(delta)}/mo"
                summary = (
                    f"Small increase in monthly investing "
                    f"may help reach this goal in {years} years.")
                why = (
                    f"You currently invest about "
                    f"${int(current_budget)}/month, "
                    f"while this goal may require "
                    f"around ${int(monthly_needed)}/month.")
                impact = (
                    f"Increasing monthly investing "
                    f"may improve the probability "
                    f"of reaching this goal.")
            elif gap_type == "challenging":
                headline = f"{goal_name} may need faster investing"
                summary = (
                    f"Current pace may be insufficient "
                    f"for your target timeline.")
                why = (
                    f"You currently invest about "
                    f"${int(current_budget)}/month, "
                    f"while this goal may require "
                    f"around ${int(monthly_needed)}/month.")
                impact = (
                    f"Increasing monthly investing "
                    f"may improve the probability "
                    f"of reaching this goal.")
            elif gap_type == "aggressive":
                headline = f"{goal_name} target is very ambitious"
                summary = (
                    f"This goal may require significantly "
                    f"higher contributions or a longer timeline.")
                why = (
                    f"You currently invest about "
                    f"${int(current_budget)}/month, "
                    f"while this goal may require "
                    f"around ${int(monthly_needed)}/month.")
                impact = (
                    f"Increasing monthly investing "
                    f"may improve the probability "
                    f"of reaching this goal.")
            else:
                headline = f"{goal_name} goal may be unrealistic"
                summary = (
                    f"Current target likely requires "
                    f"an unusually high investing pace.")
                why = (
                    f"You currently invest about "
                    f"${int(current_budget)}/month, "
                    f"while this goal may require "
                    f"around ${int(monthly_needed)}/month.")
                impact = (
                    f"Increasing monthly investing "
                    f"may improve the probability "
                    f"of reaching this goal.")
            items.append(
                InsightCard(
                    id=str(uuid.uuid4()),
                    category="goals",
                    priority=max(60, int(100 - probability)),
                    severity=severity,
                    emoji="🎯",
                    headline=headline,
                    summary=summary,
                    why_it_matters=why,
                    impact=impact,
                    action_label="🚀 Improve Plan",
                    callback="goal_fix"))
        return items


    def risk_insights(self):
        items = []
        volatility = (self.risk.get("volatility", 15))
        risk_pref = (self.portfolio_profile.risk_tolerance or "medium")
        thresholds = {
            "low": 18,
            "medium": 28,
            "high": 40}
        limit = thresholds.get(risk_pref, 28)
        if volatility <= limit:
            return items
        excess = round(volatility - limit, 1)
        items.append(
            InsightCard(
                id=str(uuid.uuid4()),
                category="risk",
                priority=88,
                severity=(
                    "critical"
                    if excess > 15
                    else "high"),
                emoji="🛡",
                headline="Portfolio risk may exceed your comfort level",
                summary=(
                    f"Current volatility is "
                    f"{round(volatility, 1)}%, above your "
                    f"{risk_pref}-risk profile."
                    f"Large market swings may become harder to tolerate."),
                why_it_matters=(
                    "Higher volatility increases "
                    "the chance of large losses "
                    "during market downturns."),
                impact=(
                    "Rebalancing may reduce "
                    "drawdown risk"),
                action_label="⚖️ Reduce Risk",
                callback="rebalance_now"))
        return items

    def diversification_insights(self):
        items = []
        if not self.positions:
            return items
        largest = max(
            self.positions,
            key=lambda x: x.get("weight", 0))
        weight = largest.get("weight", 0)
        if weight < 0.45:
            return items
        ticker = largest.get("ticker", "Asset")
        items.append(
            InsightCard(
                id=str(uuid.uuid4()),
                category="diversification",
                priority=85,
                severity=(
                    "critical"
                    if weight > 0.65
                    else "high"),
                emoji="📉",
                headline=(f"{ticker} dominates portfolio"),
                summary=(
                    f"{ticker} represents "
                    f"{int(weight * 100)}% "
                    f"of total allocation."),
                why_it_matters=(
                    "Heavy concentration in one asset "
                    "can significantly increase "
                    "portfolio drawdowns."),
                impact=(
                    f"Reducing {ticker} exposure "
                    f"may improve diversification"),
                action_label="⚖️ Diversify",
                callback="rebalance_now"))
        return items

    def market_insights(self):
        items = []
        if self.regime != "bear":
            return items
        budget = (self.portfolio_profile.monthly_budget or 0)
        if budget <= 0:
            return items
        items.append(
            InsightCard(
                id=str(uuid.uuid4()),
                category="market",
                priority=40,
                severity="medium",
                emoji="📈",
                headline="Bear market may improve entry prices",
                summary=(
                    "Long-term investors often benefit "
                    "from investing during downturns."),
                why_it_matters=(
                    "Historically, investing during "
                    "bear markets improved long-term "
                    "returns after recovery periods."),
                impact=(
                    f"Deploying your "
                    f"${int(budget)}/mo plan consistently "
                    f"may improve long-term returns"),
                action_label="💰 Auto Invest",
                callback="auto_invest"))
        return items

    def behavior_insights(self):
        items = []
        if self.goals:
            return items
        items.append(
            InsightCard(
                id=str(uuid.uuid4()),
                category="behavior",
                priority=70,
                severity="medium",
                emoji="🧭",
                headline="Portfolio has no financial goals",
                summary=(
                    "Your investments currently "
                    "have no defined target."),
                why_it_matters=(
                    "Clear goals improve discipline, "
                    "risk management, and "
                    "long-term consistency."),
                impact=(
                    "Adding goals enables "
                    "AI planning and optimization"),
                action_label="🎯 Add Goal",
                callback="goal_settings"))
        return items