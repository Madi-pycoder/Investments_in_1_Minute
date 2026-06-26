import uuid
from Explanation.financial_models import InsightCard
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
                headline = f"Для цели «{goal_name}» может понадобиться ещё ${int(delta)}/мес"
                summary = (
                    f"Небольшое увеличение ежемесячных вложений "
                    f"может помочь достичь цели за {years} лет.")
                why = (
                    f"Сейчас вы инвестируете около "
                    f"${int(current_budget)}/мес, "
                    f"а для достижения цели может понадобиться "
                    f"около ${int(monthly_needed)}/мес.")
                impact = (
                    "Увеличение регулярных вложений "
                    "повысит вероятность достижения цели.")
            elif gap_type == "challenging":
                headline = f"Для цели «{goal_name}» текущего темпа может не хватить"
                summary = (
                    "При текущих вложениях достичь цели "
                    "в заданный срок может быть сложно.")
                why = (
                    f"Сейчас вы инвестируете около "
                    f"${int(current_budget)}/мес, "
                    f"а для достижения цели может понадобиться "
                    f"около ${int(monthly_needed)}/мес.")
                impact = (
                    "Увеличение регулярных вложений "
                    "повысит вероятность достижения цели.")
            elif gap_type == "aggressive":
                headline = f"Цель «{goal_name}» выглядит очень амбициозной"
                summary = (
                    "Для её достижения могут потребоваться "
                    "значительно большие вложения или более долгий срок.")
                why = (
                    f"Сейчас вы инвестируете около "
                    f"${int(current_budget)}/мес, "
                    f"а для достижения цели может понадобиться "
                    f"около ${int(monthly_needed)}/мес.")
                impact = (
                    "Увеличение регулярных вложений "
                    "повысит вероятность достижения цели.")
            else:
                headline = f"Цель «{goal_name}» сейчас выглядит труднодостижимой"
                summary = (
                    "При текущих параметрах цель может требовать "
                    "слишком высокой скорости накопления капитала.")
                why = (
                    f"Сейчас вы инвестируете около "
                    f"${int(current_budget)}/мес, "
                    f"а для достижения цели может понадобиться "
                    f"около ${int(monthly_needed)}/мес.")
                impact = (
                    "Увеличение регулярных вложений "
                    "повысит вероятность достижения цели.")
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
                    action_label="🚀 Улучшить план",
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
                headline="Риск портфеля может быть выше комфортного уровня",
                summary=(
                    f"Текущая волатильность составляет "
                    f"{round(volatility, 1)}%, что выше "
                    f"вашего уровня риска ({risk_pref})."),
                why_it_matters=(
                    "При сильных падениях рынка стоимость "
                    "портфеля может снижаться заметнее, чем ожидается."),
                impact=(
                    "Ребалансировка может сделать "
                    "портфель более стабильным.")))
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
                headline=f"{ticker} занимает слишком большую долю портфеля",
                summary=(
                    f"На {ticker} приходится "
                    f"{int(weight * 100)}% всех инвестиций."),
                why_it_matters=(
                    "Если с этим активом возникнут проблемы, "
                    "это может сильно повлиять на весь портфель."),
                impact=(
                    "Более равномерное распределение "
                    "может снизить риск."),
                action_label="📦 Диверсифицировать",
                callback="rebalance_now"))
        return items

    def market_insights(self):
        items = []
        if self.regime != "Снижение рынка 📉":
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
                headline="Падение рынка может быть возможностью для покупок",
                summary=(
                    "Многие долгосрочные инвесторы продолжают "
                    "покупать активы даже во время просадок."),
                why_it_matters=(
                    "Исторически покупки во время спадов "
                    "часто приносили хороший результат "
                    "после восстановления рынка."),
                impact=(
                    f"Регулярное инвестирование по "
                    f"${int(budget)}/мес может помочь "
                    f"накопить больше капитала в будущем."),
                action_label="💰 Авто-Инвестирование",
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
                headline="У портфеля пока нет финансовой цели",
                summary=(
                    "Пока не указано, для чего именно "
                    "создаётся капитал."),
                why_it_matters=(
                    "Цели помогают выбрать подходящий риск, "
                    "сумму вложений и срок инвестирования."),
                impact=(
                    "После добавления цели ИИ сможет "
                    "давать более точные рекомендации."),
                action_label="🎯 Добавить цель",
                callback="goal_settings"))
        return items
