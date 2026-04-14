from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import keyboards as kb
import requets as rq

router = Router()


class Mode(StatesGroup):
    waiting_for_ticker = State()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id)
    await message.answer(
        f'Salam, {message.from_user.first_name}!'
        f' From which stock would you like to start? Write down the ticker of the stock to start!',
        reply_markup = kb.maind)


@router.callback_query(F.data == "analyze_again")
async def analyze_again(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not data.get("type"):
        await callback.message.answer("Choose mode first:", reply_markup=kb.maind)
        return

    await state.set_state(Mode.waiting_for_ticker)
    await callback.answer()
    await callback.message.answer("Enter ticker:")


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.answer()
        await callback.message.answer("🏠 Main menu:", reply_markup=kb.maind)
