import time
from MainEngines.robo_engine import RoboAdvisor
from ProfileData.user_profile import get_user_profile, create_user_profile, get_portfolio_profile, \
    create_portfolio_profile
from VisualFeatures import keyboards as kb
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from Portfolio_info.portfolio_compute import compute_portfolio_metrics
from Portfolio_info.portfolio_data import load_portfolio_data
from ProjectDataBase.cache import diagnosis_cache


class ProfileSetup(StatesGroup):
    income = State()
    budget = State()
    risk = State()

router = Router()

def get_diagnosis_cached(portfolio_id):
    item = diagnosis_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > 60:
        return None
    return item["data"]




@router.callback_query(F.data == "what_if")
async def what_if_flow(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🧮 Анализирую сценарии...")
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")
    if portfolio_id is None:
        await callback.message.answer("Портфель не найден.")
        return
    portfolio_data = await load_portfolio_data(portfolio_id)
    metrics = get_diagnosis_cached(portfolio_id)
    if metrics is None:
        metrics = await compute_portfolio_metrics(portfolio_data)
        diagnosis_cache[portfolio_id] = {
            "data": metrics,
            "ts": time.time()}
    user_id = callback.from_user.id
    user_profile = await get_user_profile(user_id)
    if not user_profile:
        user_profile = await create_user_profile(user_id)
    portfolio_profile = await get_portfolio_profile(portfolio_id)
    if portfolio_profile is None:
        portfolio_profile = await create_portfolio_profile(portfolio_id)
    robo = RoboAdvisor(user_profile, portfolio_profile,
            metrics, portfolio_data)
    scenarios = robo.run_what_if()
    if not scenarios:
        await callback.message.answer(
            "🎯 Пока нет финансовых целей.\n\n"
            "Добавьте первую цель, чтобы увидеть сценарии достижения.",
            reply_markup=kb.add_goal,)
        return
    text = (
        "🧮 Сценарии достижения целей\n\n"
        "Посмотрите, какие изменения сильнее всего повлияют на вероятность успеха.\n\n")
    for goal_data in scenarios:
        goal_name = goal_data["goal"]
        text += f"🎯 {goal_name}\n\n"
        scenario_list = goal_data.get("scenarios") or []
        if not scenario_list:
            text += "Нет доступных сценариев.\n\n"
            continue
        for scenario in scenario_list:
            delta = scenario.get("delta", 0)
            if delta > 0:
                emoji = "🟢"
                delta_text = f"+{delta}%"
            elif delta < 0:
                emoji = "🔴"
                delta_text = f"{delta}%"
            else:
                emoji = "⚪"
                delta_text = "0%"
            text += (
                f"{emoji} {scenario['scenario']}\n"
                f"Вероятность: {scenario['probability']}%\n"
                f"Изменение: {delta_text}\n\n")
    await callback.message.answer(text, reply_markup=kb.portfolio_dashboard)