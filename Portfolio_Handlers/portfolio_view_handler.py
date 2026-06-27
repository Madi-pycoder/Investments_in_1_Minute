from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.state import StatesGroup, State
from Portfolio_info.portfolio_compute import compute_portfolio_metrics
from Portfolio_info.portfolio_data import load_portfolio_data, get_portfolio_data_cached
from MainEngines.portfolio_view import build_portfolio_text
from ProjectDataBase.analytics import AnalyticsService
from ProjectDataBase.cache import (portfolio_cache, portfolio_data_cache, diagnosis_cache,
    get_portfolio_view_cached, get_cached_diagnosis, PORTFOLIO_VIEW_CACHE, DIAGNOSIS_IN_PROGRESS)
from VisualFeatures import keyboards as kb
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
    await callback.answer("📊 Загружаю портфель...")
    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")
    if portfolio_id is not None:
        portfolio_id = int(portfolio_id)
    if not portfolio_id:
        await callback.message.answer(
            "💼 У вас пока нет портфеля\n"
            "Создайте демо-портфель и сможете:\n"
            "• отслеживать инвестиции\n"
            "• получать персональные рекомендации\n"
            "• строить план достижения целей")
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
            "💼 У вас пока нет портфеля\n"
            "Создайте демо-портфель и сможете:\n"
            "• отслеживать инвестиции\n"
            "• получать персональные рекомендации\n"
            "• строить план достижения целей")
        await callback.message.answer(kb.create_demo)
        return
    cached = get_cached(portfolio_id)
    if cached:
        data, metrics = cached
    else:
        metrics = get_cached_diagnosis(portfolio_id)
        if not metrics:
            metrics = await compute_portfolio_metrics(data)
            diagnosis_cache[portfolio_id] = {
                "data": metrics,
                "ts": time.time()}
    asyncio.create_task(preload_diagnosis(portfolio_id, data))
    if not portfolio_id:
        await callback.message.answer(
            "💼 У вас пока нет портфеля\n"
            "Создайте демо-портфель и сможете:\n"
            "• отслеживать инвестиции\n"
            "• получать персональные рекомендации\n"
            "• строить план достижения целей")
        await callback.message.answer(kb.create_demo)
        return
    positions = data.get("positions") or []
    if not positions:
        await state.set_state(Mode.waiting_for_ticker)
        await state.update_data(type="stocks")
        await callback.message.answer(
            f"💰 Свободные средства: ${data['portfolio'].cash}\n"
            "📭 В портфеле пока нет активов.\n\n"
            "Введите тикер компании\n\n"
            "ИЛИ выберите готовую подборку 👇",
            reply_markup=kb.stock_categories)
        return
    if not metrics:
        await callback.message.answer(
            "⚠️ Не удалось получить часть данных.\n\n"
            "Показываю упрощённый анализ.")
        return
    cached_view = get_portfolio_view_cached(portfolio_id)
    if cached_view:
        text, keyboard = cached_view
    else:
        text, keyboard = await build_portfolio_text(data, metrics, portfolio_id)
        PORTFOLIO_VIEW_CACHE[portfolio_id] = {
            "data": (text, keyboard),
            "ts": time.time()}
    await callback.message.answer(text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="portfolio.opened",
            event_data={"portfolio_id": portfolio_id}))