import asyncio
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from Portfolio_info.portfolio_data import load_portfolio_data
from ProjectDataBase.analytics import AnalyticsService
from ProjectDataBase.cache import diagnosis_cache
from ProfileData.profile_states import ProfileSetup
from ProfileData.user_profile import (get_portfolio_profile,
                                      create_portfolio_profile, create_user_profile, get_user_profile,
                                      update_portfolio_profile)
from MainEngines.robo_engine import RoboAdvisor
from MainEngines.auto_invest_engine import run_auto_invest_for_user, get_cached_metrics
import time

router = Router()

async def preload_diagnosis(portfolio_id, data):
    try:
        metrics = await get_cached_metrics(portfolio_id, data)
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

def safe_percent(v):
    return round(v, 2) if isinstance(v, (int, float)) else 0

async def build_auto_invest_response(user_id, portfolio_id):
    user_profile = await get_user_profile(user_id)
    if not user_profile:
        user_profile = await create_user_profile(user_id)
    portfolio_profile = await get_portfolio_profile(portfolio_id)
    if not portfolio_profile:
        portfolio_profile = await create_portfolio_profile(portfolio_id)
    income = user_profile.income
    budget = portfolio_profile.monthly_budget
    risk = portfolio_profile.risk_tolerance
    if income is None:
        return "NEED_INCOME", None
    if budget is None or budget <= 0:
        return "NEED_BUDGET", None
    if not risk:
        return "NEED_RISK", None
    data = await load_portfolio_data(portfolio_id)
    metrics = await AnalyticsService.measure(
        user_id,
        "metrics.compute",
        coro=get_cached_metrics(portfolio_id, data),
        category="performance",
        event_data={
            "portfolio_id": portfolio_id,
            "positions": len(data.get("positions") or []),
            "goals": len(data.get("goals") or [])})
    if not metrics:
        return "⚠️ Data temporarily unavailable", None
    robo = RoboAdvisor(
        user_profile=user_profile,
        portfolio_profile=portfolio_profile,
        metrics=metrics,
        data=data)
    result = robo.build_auto_invest_plan()
    if not result["ok"]:
        text = "❌ Cannot build Monthly Investment Plan\n\n"
        reason_map = {
            "no_positions": "• Portfolio has no positions",
            "no_budget": "• Monthly budget not configured",
            "empty_plan": (
                "• Portfolio is relatively balanced.\n"
                "New investments will follow strategic allocation")}
        text += reason_map.get(result["status"], "• Unknown error")
        return text, None
    plan = result["plan"]
    total = sum(x["amount"] for x in plan)
    text = ("🚀 Monthly Investing Plan\n\n"
            "Based on your goals, risk profile and current portfolio.")
    text += f"💰 Monthly: ${round(total, 2)}\n\n"
    for x in plan:
        text += f"+ ${x['amount']} → {x['ticker']}\n"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                    text="🚀 Execute Monthly Investment Plan",
                    callback_data="start_auto_invest")]])
    return text, keyboard

@router.callback_query(F.data == "auto_invest")
async def auto_invest_flow(callback: CallbackQuery, state: FSMContext):
    await callback.answer(
        "🤖 Building your monthly investment plan...")
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
    await state.set_data({"portfolio_id": portfolio_id})
    if user_profile.income is None:
        await state.set_state(ProfileSetup.income)
        await callback.message.answer(
            "💰 What's your monthly income?")
        return
    current_budget = portfolio_profile.monthly_budget or 0
    if current_budget > 0:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                        text=f"✅ Keep ${round(current_budget, 2)}",
                        callback_data="keep_budget")],
                [InlineKeyboardButton(
                    text="✏️ Change monthly investment",
                    callback_data="change_budget")]])
        await callback.message.answer(
            "💸 Monthly investment detected.\n\n"
            f"Current amount: ${round(current_budget, 2)}\n\n"
            "Do you want to keep it or change it?",
            reply_markup=keyboard)
        return
    await state.set_state(ProfileSetup.budget)
    await callback.message.answer(
        "💸 How much do you want to invest monthly?")


@router.callback_query(F.data == "keep_budget")
async def keep_budget(callback: CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    portfolio_id = int(data_state["portfolio_id"])
    text, keyboard = await build_auto_invest_response(
        callback.from_user.id,
        portfolio_id)
    if text == "NEED_RISK":
        await state.set_state(ProfileSetup.risk)
        await callback.message.answer(
            "📊 What's your risk level?\n\n"
            "low / medium / high")
        return
    await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "change_budget")
async def change_budget(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileSetup.budget)
    await callback.message.answer(
        "💸 Enter new monthly investment amount:")


@router.callback_query(F.data == "start_auto_invest")
async def start_auto_invest(callback: CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")
    if portfolio_id is not None:
        portfolio_id = int(portfolio_id)
    user_id = callback.from_user.id
    profile = await get_portfolio_profile(portfolio_id)
    if not profile:
        profile = await create_portfolio_profile(portfolio_id)
    if not profile.auto_invest_enabled:
        await update_portfolio_profile(portfolio_id, auto_invest_enabled=True)
    await callback.answer("🚀 Executing Monthly Investment Plan...")
    result = await run_auto_invest_for_user(user_id, portfolio_id)
    status = result["status"]
    if status == "executed":
        text = "🚀 Monthly Investment Plan Executed\n\n"
        for t in result["trades"]:
            text += f"BUY ${t['amount']} {t['ticker']}\n"
        text += "\n✅ Monthly Investments enabled"
        await callback.message.answer(text)
    else:
        await callback.message.answer(f"⚠️ Plan Executing failed: {status}")
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=user_id,
            event_name="auto_invest.executed",
            category="auto_invest",
            success=(status == "executed"),
            event_data={
                "portfolio_id": portfolio_id,
                "status": status,
                "invested": result.get("invested", 0),
                "trades_count": len(result.get("trades", [])),
                "auto_invest_enabled": True}))