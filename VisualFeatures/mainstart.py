from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from VisualFeatures import keyboards as kb
from ProjectDataBase import backend as rq

router = Router()

class Mode(StatesGroup):
    waiting_for_ticker = State()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id)
    await message.answer(
        "📈 Smart Investing Assistant\n\n"
        "Analyze stocks and ETFs.\n"
        "Track your portfolio\n."
        "Get valuable investment insights\n."
        "Built for long-term investors\n\n."
        "👇 Choose where to start:",
        reply_markup = kb.maind)


@router.callback_query(F.data == "analyze_again")
async def analyze_again(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("type"):
        await callback.message.answer("Choose mode first:", reply_markup=kb.maind)
        return
    await state.set_state(Mode.waiting_for_ticker)
    if data.get("type") == "stocks":
        await callback.message.answer(
            "📈 Enter another stock ticker:",
            reply_markup=kb.popular_stocks)
    else:
        await callback.message.answer(
            "🧩 Enter another ETF ticker:",
            reply_markup=kb.popular_etfs)


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        portfolio_id = data.get("portfolio_id")
        await state.clear()
        if portfolio_id is not None:
            await state.set_data({ "portfolio_id": portfolio_id})
        await callback.answer()
        await callback.message.answer("🏠 Main menu:", reply_markup=kb.maind)