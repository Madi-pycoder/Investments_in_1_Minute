import asyncio
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from ProjectDataBase.analytics import AnalyticsService
from VisualFeatures import keyboards as kb
from ProjectDataBase import backend as rq

router = Router()

class Mode(StatesGroup):
    waiting_for_ticker = State()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id)
    await message.answer(
        "📈 Не знаете, что купить?\n\n"
        "За 30 секунд покажем:\n\n"
        "• стоит ли покупать акцию или ETF\n"
        "• насколько рискован актив\n"
        "• соответствует ли он Шариату\n"
        "• понятный итог без финансового жаргона\n\n"
        "👇 Выберите, что хотите проверить",
        reply_markup=kb.maind)
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=message.from_user.id,
            event_name="bot.opened",
            category="navigation"))


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        portfolio_id = data.get("portfolio_id")
        await state.clear()
        if portfolio_id is not None:
            await state.set_data({ "portfolio_id": portfolio_id})
        await callback.answer()
        await callback.message.answer(
            "🏠 Главное меню",
            reply_markup=kb.maind)