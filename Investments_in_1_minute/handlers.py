from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from market import get_stock_info, get_etf_info

import keyboards as kb
import bazadannyh.requets as rq

router = Router()

class Reg(StatesGroup):
    name = State()
    name_demo = State()

class Log(StatesGroup):
    name = State()
    name_demo = State()

class Mode1(StatesGroup):
    type = State("stocks")

class Mode2(StatesGroup):
    type = State("etfs")

@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id)
    await message.reply(
        f'Salam, {message.from_user.first_name}!'
        f' From which stock would you like to start? Write down the ticker of the stock to start!',
        reply_markup = kb.maind)


@router.callback_query(F.data == "stocks")
async def cmd_stocks(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Mode1.type)
    await state.update_data(type="stocks")

    await callback.message.answer("You chose stocks, now, you can analyze stocks!", show_alert=True)
    await callback.message.answer("Write down the ticker of the stock to start!")

@router.message()
async def ticker_handler(message: Message, state: FSMContext):

    mode = await state.get_data()
    mode_type = mode.get("type")

    ticker = message.text.strip().upper()

    if mode_type == "stocks":
        data = await get_stock_info(ticker)

        if "error" in data:
            await message.answer("Тикер не найден 😢")
            return

        text = f"""
        📊 {data['name']} ({data['ticker']})

        💵 Price: {data['price']}$

        📘 Fundamentals
        • Debt/Equity: {data['debt_to_equity']}
        • P/E: {data['pe']}
        • EPS: {data['eps']}
        • Market Cap: {data['market_cap']}
        • Dividends: {data['dividends']}$
        • Earnings: {data['earnings_date']}

        📈 Growth
        • 1D: {data['growth']['1D']}%
        • 5D: {data['growth']['5D']}%
        • 1M: {data['growth']['1M']}%
        • 6M: {data['growth']['6M']}%
        • 1Y: {data['growth']['1Y']}%
        • 5Y: {data['growth']['5Y']}%
        """

        await message.answer(text)
        return


    if mode_type == "etfs":
        data = await get_etf_info(ticker)

        if "error" in data:
            await message.answer("Тикер не найден 😢")
            return

        text = f"""
        🧩 {data['name']} ({data['ticker']})

        💵 Price: {data['price']}$

        📦 ETF Data
        • NAV: {data['nav']}
        • Net Assets: {data['net_assets']}
        • P/E: {data['pe']}
        • Expense Ratio: {data['expense']}

        📈 Growth
        • 1D: {data['growth']['1D']}%
        • 5D: {data['growth']['5D']}%
        • 1M: {data['growth']['1M']}%
        • 6M: {data['growth']['6M']}%
        • 1Y: {data['growth']['1Y']}%
        • 5Y: {data['growth']['5Y']}%
        """

        await message.answer(text)
        return


@router.callback_query(F.data == "etfs")
async def cmd_etfs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Mode2.type)
    await state.update_data(type="etfs")

    await callback.message.answer("You chose ETFs, now, you can analyze ETFs!", show_alert=True),
    await callback.message.answer("Write down the ticker of the ETF to start!")


@router.callback_query(F.data == "create demo")
async def cmd_create_demo(callback: CallbackQuery):
    await callback.message.answer("Let's create demo portfolio!", show_alert=True),
    await callback.message.answer("Tap on /registrate to start creating own demo-portfolio!")

@router.message(Command('registrate'))
async def cmd_ownername(message: Message, state: FSMContext):
    await rq.set_user(message.from_user.id)
    await state.set_state(Reg.name)
    await message.answer("Enter owner's full name")

@router.message(Reg.name)
async def cmd_demoname(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Reg.name_demo)
    await message.answer("Enter demo-portfolio's full name")

@router.message(Reg.name_demo)
async def cmd_regend(message: Message, state: FSMContext):

    await state.update_data(name_demo=message.text)
    data = await state.get_data()

    portfolio_id = await rq.create_demo_portfolio(
        tg_id=message.from_user.id,
        owner_name=data['name'],
        demo_name=data['name_demo']
    )

    await message.answer(
        f"✅ Demo-portfolio created!\n\n"
        f"Owner: {data['name']}\n"
        f"Portfolio: {data['name_demo']}\n"
        f"Start balance: $10 000\n"
        f"ID: {portfolio_id}"
    )

    await state.clear()


@router.callback_query(F.data == "login demo")
async def cmd_login(callback: CallbackQuery):
    await callback.message.answer("Wanna to log in old demo? No problem!", show_alert=True),
    await callback.message.answer("Tap on /login to to login to old demo-portfolio!")

@router.message(Command('login'))
async def cmd_ownername(message: Message, state: FSMContext):
    await state.set_state(Log.name)
    await message.answer("Enter owner's full name")

@router.message(Log.name)
async def cmd_demoname(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Log.name_demo)
    await message.answer("Enter demo-portfolio's full name")

@router.message(Log.name_demo)
async def cmd_logend(message: Message, state: FSMContext):

    await state.update_data(name_demo=message.text)
    data = await state.get_data()

    portfolio, status = await rq.login_demo_portfolio(
        tg_id=message.from_user.id,
        demo_name=data['name_demo']
    )

    if not portfolio:
        await message.answer("❌ Portfolio not found. Try again or create new one.")
        await state.clear()
        return

    await message.answer(
        f"✅ Login successful!\n\n"
        f"Portfolio ID: {portfolio.id}\n"
        f"Balance: ${portfolio.cash}\n"
        f"Last update: {portfolio.updated_at}"
    )

    await state.clear()