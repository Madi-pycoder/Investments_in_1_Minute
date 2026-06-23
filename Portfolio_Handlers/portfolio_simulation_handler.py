import time
from VisualFeatures import keyboards as kb
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from Portfolio_info.portfolio_compute import compute_portfolio_metrics
from Portfolio_info.portfolio_data import load_portfolio_data
from ProjectDataBase.analytics import AnalyticsService
from ProjectDataBase.cache import diagnosis_cache
from MainMetricsComputingFeatures.riskmanagement import (calculate_portfolio_risk,
    monte_carlo_portfolio)
from ProfileData.user_profile import (get_user_profile, create_portfolio_profile,
    get_portfolio_profile, create_user_profile)
from MainEngines.robo_engine import RoboAdvisor

class ProfileSetup(StatesGroup):
    income = State()
    budget = State()
    risk = State()
router = Router()

async def preload_diagnosis(portfolio_id,data):
    try:
        metrics = await compute_portfolio_metrics(data)
        diagnosis_cache[portfolio_id] = {"data": metrics, "ts": time.time()}
    except Exception as e:
        print("preload_diagnosis ERROR:", e)

def get_diagnosis_cached(portfolio_id):
    item = diagnosis_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > 60:
        return None
    return item["data"]

def safe_percent(v):
    return round(v, 2) if isinstance(v, (int, float)) else 0



async def compare_portfolios(current_positions, target_weights):
    current_risk = await calculate_portfolio_risk(current_positions)
    total_value = sum(p["value"] for p in current_positions)
    rebalanced_positions = []
    for p in current_positions:
        ticker = p["ticker"]
        target_weight = target_weights.get(ticker, 0)
        rebalanced_positions.append({
            "ticker": ticker,
            "value": total_value * target_weight,
            "weight": target_weight})
    rebalanced_risk = await calculate_portfolio_risk(rebalanced_positions)
    rebalanced_mc = await monte_carlo_portfolio(rebalanced_positions)
    return {
        "current": {
            "return": safe_percent(current_risk.get("expected_return", 0)),
            "risk": current_risk.get("volatility")},
        "rebalanced": {
            "return": rebalanced_mc.get("expected_return"),
            "risk": rebalanced_risk.get("volatility")}}


@router.callback_query(F.data == "what_if")
async def what_if_flow(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🧮 Рассчитываю сценарии...")
    data_state = await state.get_data()
    user_id = callback.from_user.id
    portfolio_id = data_state.get("portfolio_id")
    user_profile = await get_user_profile(user_id)
    data = await load_portfolio_data(portfolio_id)
    if not user_profile:
        user_profile = await create_user_profile(user_id)
    portfolio_profile = await get_portfolio_profile(portfolio_id)
    if not portfolio_profile:
        portfolio_profile = await create_portfolio_profile(portfolio_id)
    user_id = callback.from_user.id
    if portfolio_id is not None:
        portfolio_id = int(portfolio_id)
    metrics = get_diagnosis_cached(portfolio_id)
    if not metrics:
        data = await load_portfolio_data(portfolio_id)
        metrics = await AnalyticsService.measure(
            user_id=user_id,
            event_name="metrics.compute",
            coro=compute_portfolio_metrics(data),
            category="performance",
            event_data={
                "portfolio_id": portfolio_id,
                "positions": len(data.get("positions") or []),
                "goals": len(data.get("goals") or [])})
    if not metrics:
        await callback.message.answer(
            "⚠️ Не удалось получить часть данных.\n\n"
            "Показываю упрощённый анализ.")
        return
    robo = RoboAdvisor(
        user_profile=user_profile,
        portfolio_profile=portfolio_profile,
        metrics=metrics, data=data)
    scenarios = robo.run_what_if()
    if not scenarios:
        await callback.message.answer(
            "🎯 Пока нет финансовых целей"
            "Добавьте цель, чтобы получать персональные рекомендации и прогнозы",
        reply_markup=kb.add_goal)
        return
    text = ("🧮 Сценарии развития\n\n"
            "Посмотрите, как разные решения могут повлиять на ваши финансовые цели\n\n")
    for goal_data in scenarios:
        if goal_data.get("status") == "already_safe":
            text += (
                f"🎯 {goal_data['goal']}\n"
                f"✅ Цель уже выглядит достижимой"
                f"({goal_data['probability']}%)\n\n")
            continue
        text += f"🎯 {goal_data['goal']}\n\n"
        scenario_list = goal_data.get("scenarios", [])
        if not isinstance(scenario_list, list):
            continue
        for s in scenario_list:
            if not isinstance(s, dict):
                continue
            delta = s.get("delta", 0)
            delta_str = (
                f"(+{delta}%)"
                if delta > 0
                else f"({delta}%)")
            text += (
                f"{s['scenario']}: "
                f"{s['probability']}% "
                f"{delta_str}\n\n")
    await callback.message.answer(text, reply_markup=kb.portfolio_dashboard)