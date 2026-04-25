from robo_engine import RoboAdvisor

class FinancialBrain:

    def __init__(self, robo: RoboAdvisor):
        self.robo = robo

        self.profile = robo.profile
        self.metrics = robo.metrics

    def get_next_actions(self):

        actions = []

        issues = self.robo.get_issues()
        for i in issues:
            actions.append({
                "priority": "high",
                "type": "fix",
                "text": i
            })

        regime_insight = self.get_regime_insight()
        if regime_insight:
            actions.append(regime_insight)



        nudges = self.robo.get_nudges() or []
        for n in nudges:
            actions.append({
                "priority": self.map_priority(n["type"]),
                "type": "improve",
                "text": n["text"]
            })

        plan = self.robo.build_auto_invest_plan()
        if plan:
            total = sum(x["amount"] for x in plan)

            if total < 100:
                actions.append({
                    "priority": "medium",
                    "type": "invest",
                    "text": "Increase monthly investments"
                })
            else:
                actions.append({
                    "priority": "low",
                    "type": "invest",
                    "text": "Auto-Invest is working well"
                })

        goal_analysis = self.robo.analyze_goals()

        if goal_analysis:
            worst = min(goal_analysis, key=lambda x: x["simulation"]["probability"])
            prob = worst["simulation"]["probability"]

            if prob < 40:
                actions.append({
                    "priority": "high",
                    "type": "goal",
                    "text": f"Improve goal: {worst['goal']['name']}"
                })

        return self.rank_actions(actions)



    def map_priority(self, nudge_type):
        return {
            "critical": "high",
            "improve": "medium",
            "good": "low"
        }.get(nudge_type, "low")


    def rank_actions(self, actions):

        priority_order = {
            "high": 3,
            "medium": 2,
            "low": 1
        }

        actions.sort(
            key=lambda x: priority_order.get(x["priority"], 0),
            reverse=True
        )

        return actions[:3]



    def build_summary(self):

        actions = self.get_next_actions()

        if not actions:
            return "✅ Everything looks good. Keep investing."

        text = "🧠 What to do next:\n\n"

        for a in actions:
            emoji = {
                "high": "🚨",
                "medium": "⚠️",
                "low": "✅"
            }.get(a["priority"], "•")

            text += f"{emoji} {a['text']}\n"

        return text

    def get_regime_insight(self):
        regime = self.robo.regime

        if regime == "crisis":
            return {
                "priority": "high",
                "text": "Market in crisis → reduce risk & invest gradually"
            }

        if regime == "bear":
            return {
                "priority": "medium",
                "text": "Bear market → focus on accumulation"
            }

        if regime == "bull":
            return {
                "priority": "low",
                "text": "Bull market → stay investing"
            }

        return None
