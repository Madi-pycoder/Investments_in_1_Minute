from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from ProjectDataBase import backend as rq
from VisualFeatures import keyboards as kb

router = Router()
class Trade(StatesGroup):
    waiting_for_quantity = State()
class SellFlow(StatesGroup):
    waiting_quantity = State()


@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("last_ticker"):
        await callback.message.answer("🔍 Choose an asset first\n"
        "Popular picks:", reply_markup=kb.popular_stocks)
        return
    await state.update_data(trade_type="buy")
    await state.set_state(Trade.waiting_for_quantity)
    await callback.answer()
    await callback.message.answer("Enter quantity to BUY:")


@router.callback_query(F.data == "sell")
async def sell_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("last_ticker"):
        await callback.message.answer("🔍 Choose an asset first\n"
        "Popular picks:", reply_markup=kb.popular_stocks)
        return
    await state.update_data(trade_type="sell")
    await state.set_state(Trade.waiting_for_quantity)
    await callback.answer()
    await callback.message.answer("Enter quantity to SELL:")


@router.message(Trade.waiting_for_quantity)
async def process_trade(message: Message, state: FSMContext):
    try:
        qty = float(message.text)
        if qty <= 0:
            raise ValueError
    except Exception as e:
        print("ERROR:", e)
        await message.answer("Enter valid number.")
        return
    data = await state.get_data()
    ticker = data["last_ticker"]
    price = float(data["last_price"])
    trade_type = data["trade_type"]
    portfolio_id = data.get("portfolio_id")
    if not portfolio_id:
        await message.answer("Login to demo portfolio first.", reply_markup=kb.login_demo)
        await state.clear()
        return
    portfolio = await rq.get_portfolio(portfolio_id)
    total = qty * price
    if trade_type == "buy":
        if portfolio.cash < total:
            await message.answer("❌ Not enough cash.\n"
                "Enter smaller quantity: ")
            return
        STOCK_CATEGORY_ID = 1
        await rq.buy_position(portfolio_id, ticker, qty, price, STOCK_CATEGORY_ID)
        await rq.update_cash(portfolio_id, portfolio.cash - total)
        await rq.add_transaction(portfolio_id, ticker, qty, price, True)
        await message.answer(f"✅ Bought {qty} {ticker} for ${total}")
        await state.clear()
    else:
        success, msg = await rq.sell_position(portfolio_id, ticker, qty)
        if not success:
            await message.answer(f"❌ {msg}\n"
                f"Try smaller quantity: ")
            return
        await rq.update_cash(portfolio_id, portfolio.cash + total)
        await rq.add_transaction(portfolio_id, ticker, qty, price, False)
        await message.answer(f"✅ Sold {qty} {ticker} for ${total}")
        await state.clear()


@router.callback_query(F.data.startswith("sell_"))
async def sell_asset(callback: CallbackQuery, state: FSMContext):
    ticker = callback.data.removeprefix("sell_")
    data = await state.get_data()
    print(await state.get_data())
    positions = await rq.get_positions(data["portfolio_id"])
    position = next((p for p in positions if p.ticker == ticker), None)
    price = await rq.get_stock_price(ticker)
    if price is None:
        await callback.message.answer("Price isn't available")
        return
    available = position.quantity if position else 0
    keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="25%",
                    callback_data="sell%25"),
                InlineKeyboardButton(
                    text="50%",
                    callback_data="sell%50")],
                [InlineKeyboardButton(
                    text="75%",
                    callback_data="sell%75"),
                InlineKeyboardButton(
                    text="100%",
                    callback_data="sell%100")]])
    await state.update_data(sell_ticker=ticker, sell_price=price,
        available_qty=available, portfolio_id=data.get("portfolio_id"))
    await state.set_state(SellFlow.waiting_quantity)
    await callback.answer()
    await callback.message.answer(f"How many shares of {ticker}?\n\n"
        f"Available: {round(available, 4)}", reply_markup=keyboard)


@router.message(SellFlow.waiting_quantity)
async def sell_quantity(message: Message, state: FSMContext, callback: CallbackQuery):
    try:
        qty = float(message.text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Enter a valid positive number")
        return
    ticker = callback.data.removeprefix("sell_")
    data = await state.get_data()
    price = await rq.get_stock_price(ticker)
    if price is None:
        await message.answer("Price isn't available")
        return
    success, msg = await rq.sell_position(portfolio_id=data["portfolio_id"],
        ticker=data['sell_ticker'], qty=qty)
    if not success:
        await message.answer(f"{msg}\n"
            "Enter smaller quantity: ")
        return
    portfolio = await rq.get_portfolio(data["portfolio_id"])
    total = qty * price
    await rq.update_cash(data["portfolio_id"], portfolio.cash + total)
    await rq.add_transaction(data["portfolio_id"], data["sell_ticker"], qty, price, False)
    await message.answer(f"✅ Sold {qty} shares of {data['sell_ticker']}")
    await state.clear()


@router.callback_query(F.data.startswith("sell%"))
async def sell_percentage(callback, state):
    percent = int(callback.data.removeprefix("sell%"))
    data = await state.get_data()
    ticker = data.get("sell_ticker")
    print(await state.get_data())
    positions = await rq.get_positions(data["portfolio_id"])
    position = next((p for p in positions
        if p.ticker == data["sell_ticker"]), None)
    if not position:
        await callback.message.answer("Position not found")
        return
    qty = position.quantity*percent/100
    portfolio = await rq.get_portfolio(data["portfolio_id"])
    price = data["sell_price"]
    if not price:
        await callback.message.answer("Price isn't available")
        return
    total = qty * price
    success, msg = await rq.sell_position(portfolio_id=data["portfolio_id"],
        ticker=data["sell_ticker"], qty=qty)
    if success:
        await rq.update_cash(data["portfolio_id"], portfolio.cash+total)
        await rq.add_transaction(data["portfolio_id"], data["sell_ticker"], qty, price, False)
        await callback.message.answer(f"✅ Sold {percent}% of {data['sell_ticker']}")
    else:
        await callback.message.answer(msg)