from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.state import StatesGroup, State
from Portfolio_info.portfolio_compute import compute_portfolio_metrics, compute_light_metrics
from Portfolio_info.portfolio_data import load_portfolio_data, get_portfolio_data_cached
from Portfolio_Handlers.portfolio_view import build_portfolio_text
from ProjectDataBase.analytics import AnalyticsService
from ProjectDataBase.cache import (portfolio_cache, portfolio_data_cache, diagnosis_cache, get_portfolio_view_cached,
                                   get_cached_diagnosis, PORTFOLIO_VIEW_CACHE, DIAGNOSIS_IN_PROGRESS)
from MainEngines.goal_engine import calculate_goal_score, get_goal_levels, get_next_milestones, build_goal_insight
from VisualFeatures import keyboards as kb
from ProjectDataBase import backend as rq
import asyncio
import time
router = Router()
class Mode(StatesGroup):
    waiting_for_ticker = State()
class ProfileSetup(StatesGroup):
    income = State()
    budget = State()
    risk = State()

def get_cached(portfolio_id):
    item = portfolio_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > 30:
        return None
    return item["data"]


async def preload_diagnosis(portfolio_id,data):
    if get_cached_diagnosis(portfolio_id):
        return
    if portfolio_id in DIAGNOSIS_IN_PROGRESS:
        return
    DIAGNOSIS_IN_PROGRESS.add(portfolio_id)
    try:
        metrics = await compute_portfolio_metrics(data)
        diagnosis_cache[portfolio_id] = {
            "data": metrics,
            "ts": time.time()}
    except Exception as e:
        print("preload_diagnosis ERROR:", e)
    finally:
        DIAGNOSIS_IN_PROGRESS.discard(portfolio_id)

@router.callback_query(F.data == 'portfolio')
async def show_portfolio(callback: CallbackQuery, state: FSMContext):
    await callback.answer("⚡ Loading Portfolio Data...")
    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")
    if portfolio_id is not None:
        portfolio_id = int(portfolio_id)
    if not portfolio_id:
        await callback.message.answer(
            "💼 No portfolio connected yet\n"
            "Create a free demo portfolio to:\n"
            "• Track investments\n"
            "• Get AI advice\n"
            "• Build monthly plans")
        await callback.message.answer(kb.create_demo)
        return
    data = get_portfolio_data_cached(portfolio_id)
    if not data:
        data = await load_portfolio_data(portfolio_id)
        portfolio_data_cache[portfolio_id] = {
            "data": data,
            "ts": time.time()}
    if not portfolio_id:
        await callback.message.answer(
            "💼 No portfolio connected yet\n"
            "Create a free demo portfolio to:\n"
            "• Track investments\n"
            "• Get AI advice\n"
            "• Build monthly plans")
        await callback.message.answer(kb.create_demo)
        return
    cached = get_cached(portfolio_id)
    if cached:
        data, metrics = cached
    else:
        metrics = await compute_light_metrics(data)
        portfolio_cache[portfolio_id] = {
            "data": (data, metrics),
            "ts": time.time()}
    asyncio.create_task(preload_diagnosis(portfolio_id, data))
    if not portfolio_id:
        await callback.message.answer(
            "💼 No portfolio connected yet\n"
            "Create a free demo portfolio to:\n"
            "• Track investments\n"
            "• Get AI advice\n"
            "• Build monthly plans")
        await callback.message.answer(kb.create_demo)
        return
    positions = data.get("positions") or []
    if not positions:
        await state.set_state(Mode.waiting_for_ticker)
        await state.update_data(type="stocks")
        await callback.message.answer(
            f"💰 Cash: ${data['portfolio'].cash}\n"
            f"📭 Your portfolio is empty\n"
            f"Start by analyzing your first investment:\n\n"
            f"Popular choices:\n"
            f"AAPL\n"
            f"NVDA\n"
            f"MSFT\n",
            reply_markup=kb.popular_stocks)
        return
    if not metrics:
        await callback.message.answer(
            "⚠️ Data temporarily unavailable\n"
            "Showing simplified view")
        return
    cached_view = get_portfolio_view_cached(portfolio_id)
    if cached_view:
        text, keyboard = cached_view
    else:
        text, keyboard = await build_portfolio_text(data, metrics, portfolio_id)
        PORTFOLIO_VIEW_CACHE[portfolio_id] = {
            "data": (text, keyboard),
            "ts": time.time()
        }
    await callback.message.answer(text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="portfolio.opened",
            event_data={"portfolio_id": portfolio_id}))


@router.callback_query(F.data =="goal_view")
async def show_goals(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    portfolio_id = data["portfolio_id"]
    portfolio_data = get_portfolio_data_cached(portfolio_id)
    if not portfolio_data:
        portfolio_data = await load_portfolio_data(portfolio_id)
    metrics = get_cached_diagnosis(portfolio_id)
    if not metrics:
        metrics = await compute_portfolio_metrics(portfolio_data)
        diagnosis_cache[portfolio_id] = {
            "data": metrics,
            "ts": time.time()}
    goals = await rq.get_goals(portfolio_id)
    results = metrics.get("goal_results", [])
    if not goals:
        await callback.message.answer(
            "🎯 No goals connected yet",
            reply_markup=kb.add_goal)
        return
    text = ("🎯 Financial Goals\n\n"
            "Track your progress and probability of success.")
    for r in results:
        goal = r["goal"]
        sim = r["simulation"]
        if not sim:
            continue
        prob = sim["probability"]
        score = calculate_goal_score(prob, goal["years"])
        level = get_goal_levels(prob)
        milestone = get_next_milestones(metrics["total_value"],
                    goal["amount"])
        insight = build_goal_insight(r)
        text += (
            f"🎯 {goal['name']}\n"
            f"{level}\n\n"
            f"Probability of Success: {prob}%\n"
            f"Score: {score}/100\n\n"
            f"Next Milestone: \n"
            f"${milestone['amount']}({milestone['percent']}%)\n\n"
            f"💡 {insight}")
    await callback.message.answer(text, reply_markup=kb.portfolio_dashboard)