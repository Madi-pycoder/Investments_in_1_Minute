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
import ProjectDataBase.backend as rq

router = Router()
AUTO_INVEST_MESSAGES = {
    "disabled":
        "Автоинвестирование отключено",
    "no_data":
        "Недостаточно данных для анализа портфеля",
    "metrics_failed":
        "Не удалось рассчитать показатели портфеля",
    "empty_plan":
        "Портфель уже выглядит сбалансированным",
    "no_valid_trades":
        "Сейчас нет подходящих сделок",
    "zero_investment":
        "Сумма инвестирования равна нулю",
    "too_early":
        "Следующая покупка по плану ещё не наступила",
    "insufficient_cash":
        "Недостаточно свободных средств",
    "executed":
        "Инвестиции выполнены"}

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
        return ("⚠️ Не удалось получить часть данных.\n\n"
                "Показываю упрощённый анализ.", None)
    robo = RoboAdvisor(
        user_profile=user_profile,
        portfolio_profile=portfolio_profile,
        metrics=metrics,
        data=data)
    result = robo.build_auto_invest_plan()
    if not result["ok"]:
        text = "❌ Не удалось составить инвестиционный план\n\n"
        reason_map = {
            "no_positions": "• В портфеле пока нет активов",
            "no_budget": "• Не указан ежемесячный бюджет инвестирования",
            "empty_plan": (
                "• Портфель уже хорошо распределён."
                "Новые инвестиции будут добавляться пропорционально текущей стратегии.")}
        text += reason_map.get(result["status"], "• Unknown error")
        return text, None
    plan = result["plan"]
    total = sum(x["amount"] for x in plan)
    text = ("📅 План инвестирования на месяц\n\n"
            "Составлен на основе ваших целей,"
            "уровня риска и текущего портфеля.")
    text += f"💰 Планируем вложить: ${round(total, 2)}\n\n"
    for x in plan:
        text += f"• ${x['amount']} → {x['ticker']}\n"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                    text="✅ Выполнить план инвестирования",
                    callback_data="start_auto_invest")]])
    return text, keyboard

@router.callback_query(F.data == "auto_invest")
async def auto_invest_flow(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🤖 Анализируем портфель...\n"
        "Это займёт несколько секунд.")
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
            "💰 Какой у вас ежемесячный доход?\n\n"
            "Укажите сумму в долларах США.")
        return
    current_budget = portfolio_profile.monthly_budget or 0
    if current_budget > 0:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                        text=f"✅ Оставить ${round(current_budget, 2)}",
                        callback_data="keep_budget")],
                [InlineKeyboardButton(
                    text="✏️ Изменить сумму",
                    callback_data="change_budget")]])
        await callback.message.answer(
            "💸 Найдена сумма ежемесячных инвестиций\n\n"
            f"Текущий бюджет: ${round(current_budget, 2)}\n\n"
            "Использовать его для нового плана?",
            reply_markup=keyboard)
        return
    await state.set_state(ProfileSetup.budget)
    await callback.message.answer(
        "💸 Сколько вы готовы инвестировать каждый месяц?"
        "Например: 100")


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
            "📊 Какой риск вам комфортен?\n\n"
            "🟢 Низкий\n"
            "Подходит, если важна стабильность.\n\n"
            "🟡 Средний\n"
            "Баланс между ростом и риском.\n\n"
            "🔴 Высокий\n"
            "Для тех, кто готов к сильным колебаниям ради большей доходности.")
        return
    await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "change_budget")
async def change_budget(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileSetup.budget)
    await callback.message.answer(
        "💸 Введите сумму ежемесячных взносов:")


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
    await callback.message.answer("🚀 Выполняем инвестиционный план...\n"
        "Это займёт несколько секунд.")
    result = await run_auto_invest_for_user(user_id, portfolio_id)
    status = result["status"]
    if status == "executed":
        text = "✅ План успешно выполнен\n\n"
        for t in result["trades"]:
            text += f"• Куплено на ${t['amount']} → {t['ticker']}\n"
        text += "\n🔄 Автоинвестирование включено"
        text += ("⚠️ План сформирован автоматически на основе"
                 " ваших настроек и состава портфеля.")
        await callback.message.answer(text)
    else:
        message = AUTO_INVEST_MESSAGES.get(status,
            "Произошла неизвестная ошибка")
        await callback.message.answer(f"⚠️ {message}")
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
    await rq.recalculate_portfolio_value(portfolio_id)