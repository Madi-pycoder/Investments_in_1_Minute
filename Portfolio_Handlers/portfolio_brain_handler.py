import asyncio
import time
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import StatesGroup, State
from Portfolio_info.portfolio_compute import compute_portfolio_metrics
from Portfolio_info.portfolio_data import load_portfolio_data
from ProjectDataBase.analytics import AnalyticsService, build_portfolio_event_data
from ProjectDataBase.cache import diagnosis_cache
from VisualFeatures.renderer import render_insight_cards
from ProfileData.user_profile import get_user_profile, create_portfolio_profile, create_user_profile, get_portfolio_profile
from MainEngines.robo_engine import RoboAdvisor
from Explanation.financial_brain import FinancialBrain

class ProfileSetup(StatesGroup):
    income = State()
    budget = State()
    risk = State()


from VisualFeatures import keyboards as kb

router = Router()

async def preload_diagnosis(portfolio_id,data):
    try:
        metrics = await compute_portfolio_metrics(data)
        diagnosis_cache[portfolio_id] = {
            "data": metrics,
            "ts": time.time()}
    except Exception as e:
        print("preload_diagnosis ERROR:", e)

def get_diagnosis_cached(portfolio_id):
    item = diagnosis_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > 60:
        return None
    return item["data"]



@router.callback_query(F.data == "explain_portfolio")
async def explain_portfolio(callback: CallbackQuery, state: FSMContext, user_id, portfolio_id):
    await callback.answer("🧠 Analyzing...")
    user_profile = await get_user_profile(user_id)
    if not user_profile:
        user_profile = await create_user_profile(user_id)
    portfolio_profile = await get_portfolio_profile(portfolio_id)
    if not portfolio_profile:
        portfolio_profile = await create_portfolio_profile(portfolio_id)
    state_data = await state.get_data()
    portfolio_id = state_data.get("portfolio_id")
    if not portfolio_id:
        await callback.message.answer(
            "💼 No portfolio connected yet\n"
            "Create a free demo portfolio to:\n"
            "• Track investments\n"
            "• Get AI advice\n"
            "• Build monthly plans")
        await callback.message.answer(kb.create_demo)
        return
    metrics = get_diagnosis_cached(portfolio_id)
    user_id = callback.from_user.id
    data = await load_portfolio_data(portfolio_id)
    if not metrics:
        data = await load_portfolio_data(portfolio_id)
        metrics = await AnalyticsService.measure(
            user_id, "metrics.compute",
            compute_portfolio_metrics(data),
            category="performance",
            event_data=build_portfolio_event_data(
                portfolio_id=portfolio_id,
                positions=data.get("positions"),
                goals=data.get("goals"),
                metrics=metrics if metrics else None,
                risk_profile=getattr(portfolio_profile, "risk_tolerance", None),
                total_value=metrics.get("total_value", 0) if metrics else 0,
                cached_metrics=bool(get_diagnosis_cached(portfolio_id))))
    if not metrics:
        await callback.message.answer("⚠️ Analysis unavailable")
        return
    robo = RoboAdvisor(
        user_profile=user_profile,
        portfolio_profile=portfolio_profile,
        metrics=metrics,
        data=data)
    brain = FinancialBrain(robo)
    insights = brain.generate()
    text, keyboard = render_insight_cards(insights, metrics)
    await callback.message.answer(text, reply_markup=keyboard)
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id,
            "portfolio.explained",
            category="ai",
            event_data=build_portfolio_event_data(
                portfolio_id=portfolio_id,
                positions=data.get("positions"),
                goals=data.get("goals"),
                metrics=metrics,
                risk_profile=getattr(portfolio_profile, "risk_tolerance", None),
                total_value=metrics.get("total_value", 0),
                cached_metrics=True)))
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=user_id,
            event_name="portfolio.explained",
            category="ai"))


@router.callback_query(F.data == "nudges")
async def nudges_flow(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🧠 AI Coach analyzing...")
    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")
    if portfolio_id is not None:
        portfolio_id = int(portfolio_id)
    user_id = callback.from_user.id
    user_profile = await get_user_profile(user_id)
    if not user_profile:
        user_profile = await create_user_profile(user_id)
    portfolio_profile = await get_portfolio_profile(portfolio_id)
    if not portfolio_profile:
        portfolio_profile = await create_portfolio_profile(portfolio_id)
    data = await load_portfolio_data(portfolio_id)
    metrics = get_diagnosis_cached(portfolio_id)
    profile = await get_user_profile(user_id)
    if not profile:
        profile = await create_portfolio_profile(portfolio_id)
    if not metrics:
        data = await load_portfolio_data(portfolio_id)
        metrics = await AnalyticsService.measure(
            user_id, "metrics.compute",
            compute_portfolio_metrics(data),
            category="performance",
            event_data=build_portfolio_event_data(
                portfolio_id=portfolio_id,
                positions=data.get("positions"),
                goals=data.get("goals"),
                metrics=metrics if metrics else None,
                risk_profile=getattr(portfolio_profile, "risk_tolerance", None),
                total_value=metrics.get("total_value", 0) if metrics else 0,
                cached_metrics=bool(get_diagnosis_cached(portfolio_id))))
    if not metrics:
        await callback.message.answer(
            "⚠️ Data temporarily unavailable\n"
            "Showing simplified view")
        return
    robo = RoboAdvisor(
        user_profile=user_profile,
        portfolio_profile=portfolio_profile,
        metrics=metrics,
        data=data)
    nudges = robo.get_nudges()
    if not nudges:
        await callback.message.answer("No suggestions.")
        return
    text = "🧠 AI Coach\n\n"
    buttons = []
    for n in nudges:
        emoji = {
            "critical": "🚨",
            "improve": "⚠️",
            "good": "✅"}.get(n["type"], "•")
        text += f"{emoji} {n['text']}\n"
        if n["type"] != "good":
            buttons.append(
                [InlineKeyboardButton(
                    text=f"⚡ Fix {n['text'][:10]}",
                    callback_data="goal_fix")])
    await callback.message.answer(text,
    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=user_id,
            event_name="nudges_opened",
            category="ai",
            event_data=build_portfolio_event_data(
                portfolio_id=portfolio_id,
                positions=data.get("positions"),
                goals=data.get("goals"),
                metrics=metrics,
                risk_profile=getattr(profile, "risk_tolerance", None),
                total_value=metrics.get("total_value", 0),
                cached_metrics=True,
                extra={
                    "nudges_count": len(nudges),
                    "critical_count": len([n for n in nudges if n["type"] == "critical"])})))



@router.callback_query(F.data == "financial_brain")
async def financial_brain_flow(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🧠 Thinking...")
    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")
    data = await load_portfolio_data(portfolio_id)
    if portfolio_id is not None:
        portfolio_id = int(portfolio_id)
    user_id = callback.from_user.id
    user_profile = await get_user_profile(user_id)
    if not user_profile:
        user_profile = await create_user_profile(user_id)
    portfolio_profile = await get_portfolio_profile(portfolio_id)
    if not portfolio_profile:
        portfolio_profile = await create_portfolio_profile(portfolio_id)
    metrics = get_diagnosis_cached(portfolio_id)
    profile = await get_user_profile(user_id)
    if not profile:
        profile = await create_portfolio_profile(portfolio_id)
    if not metrics:
        data = await load_portfolio_data(portfolio_id)
        metrics = await AnalyticsService.measure(
            user_id,
            "metrics.compute",
            compute_portfolio_metrics(data),
            category="performance",
            event_data=build_portfolio_event_data(
                portfolio_id=portfolio_id,
                positions=data.get("positions"),
                goals=data.get("goals"),
                metrics=metrics if metrics else None,
                risk_profile=getattr(profile, "risk_tolerance", None),
                total_value=metrics.get("total_value", 0) if metrics else 0,
                cached_metrics=bool(get_diagnosis_cached(portfolio_id))
            ))
    if not metrics:
        await callback.message.answer(
            "⚠️ Data temporarily unavailable\n"
            "Showing simplified view")
        return
    robo = RoboAdvisor(
        user_profile=user_profile,
        portfolio_profile=portfolio_profile,
        metrics=metrics, data=data)
    brain = FinancialBrain(robo)
    data = await load_portfolio_data(portfolio_id)
    insights = brain.generate()
    text, keyboard = render_insight_cards(insights, metrics)
    await callback.message.answer(text, reply_markup=keyboard)
    start = time.perf_counter()
    duration = int((time.perf_counter() - start) * 1000)
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=user_id,
            event_name="ai.financial_brain_opened",
            category="ai",
            duration_ms=duration,
            event_data=build_portfolio_event_data(
                portfolio_id=portfolio_id,
                positions=data.get("positions"),
                goals=data.get("goals"),
                metrics=metrics,
                risk_profile=getattr(profile, "risk_tolerance", None),
                total_value=metrics.get("total_value", 0),
                cached_metrics=True,
                extra={"insights_count": len(insights)})))