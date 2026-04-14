from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import requets as rq
router = Router()

class Trade(StatesGroup):
    waiting_for_quantity = State()


@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    if not data.get("last_ticker"):
        await callback.message.answer("Analyze asset first.")
        return

    await state.update_data(trade_type="buy")
    await state.set_state(Trade.waiting_for_quantity)

    await callback.answer()
    await callback.message.answer("Enter quantity to BUY:")


@router.callback_query(F.data == "sell")
async def sell_handler(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    if not data.get("last_ticker"):
        await callback.message.answer("Analyze asset first.")
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
    except:
        await message.answer("Enter valid number.")
        return

    data = await state.get_data()

    ticker = data["last_ticker"]
    price = float(data["last_price"])
    trade_type = data["trade_type"]


    portfolio_id = data.get("portfolio_id")

    if not portfolio_id:
        await message.answer("Login to demo portfolio first.")
        await state.clear()
        return

    portfolio = await rq.get_portfolio(portfolio_id)

    total = qty * price

    if trade_type == "buy":

        if portfolio.cash < total:
            await message.answer("❌ Not enough cash.")
            await state.clear()
            return

        await rq.buy_position(portfolio_id, ticker, qty, price, 1)
        await rq.update_cash(portfolio_id, portfolio.cash - total)
        await rq.add_transaction(portfolio_id, ticker, qty, price, True)

        await message.answer(f"✅ Bought {qty} {ticker} for ${total}")

    else:
        success, msg = await rq.sell_position(portfolio_id, ticker, qty)

        if not success:
            await message.answer(f"❌ {msg}")
            await state.clear()
            return

        await rq.update_cash(portfolio_id, portfolio.cash + total)
        await rq.add_transaction(portfolio_id, ticker, qty, price, False)

        await message.answer(f"✅ Sold {qty} {ticker} for ${total}")