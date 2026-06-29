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
class WelcomeQuiz(StatesGroup):
    savings = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await rq.set_user(message.from_user.id)
    await state.set_state(WelcomeQuiz.savings)
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Большинство инвесторов теряют деньги\n"
        "не потому что рынок плохой,\n"
        "а потому что покупают активы вслепую.\n\n"
        "Давайте быстро посчитаем,\n"
        "сколько это может стоить именно вам.\n\n"
        "💰 Сколько у вас сейчас накоплений?\n\n"
        "Например:\n"
        "100000 тенге\n"
        "300000 тенге\n"
        "1000000 тенге")


@router.message(WelcomeQuiz.savings)
async def welcome_savings(message: Message, state: FSMContext):
    try:
        savings = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer(
            "Введите сумм числом.\n\n"
            "Например:\n"
            "100000")
        return
    await state.update_data(savings=savings)
    expected_loss = savings * 0.09
    await message.answer(
        f"📉 Если инвестировать случайно,\n"
        "или оставлять сбережения без дела"
        f"ошибки могут стоить около\n\n"
        f"≈ ${expected_loss:,.0f} в год.\n\n"
        "Хорошая новость —\n"
        "многие ошибки можно увидеть заранее.\n\n"
        "👇 Давайте проверим любую акцию или ETF.",
        reply_markup=kb.maind)
    await state.clear()


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