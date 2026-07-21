from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from ProjectDataBase import backend as rq
from VisualFeatures import keyboards as kb
from sqlalchemy import select
from ProjectDataBase.models import async_session as session, Category
import logging

logger = logging.getLogger(__name__)
router = Router()

class Trade(StatesGroup):
    waiting_for_quantity = State()
class SellFlow(StatesGroup):
    waiting_quantity = State()


@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("last_ticker"):
        await callback.message.answer(
            "📭 В портфеле пока нет активов.\n\n"
            "Введите тикер компании\n\n"
            "ИЛИ выберите готовую подборку 👇", reply_markup=kb.stock_categories)
        return
    await state.update_data(trade_type="buy")
    await state.set_state(Trade.waiting_for_quantity)
    await callback.answer()
    await callback.message.answer("Введите количество для покупки:")


@router.callback_query(F.data == "sell")
async def sell_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("last_ticker"):
        await callback.message.answer(
            "📭 В портфеле пока нет активов.\n\n"
            "Введите тикер компании\n\n"
            "ИЛИ выберите готовую подборку 👇", reply_markup=kb.stock_categories)
        return
    await state.update_data(trade_type="sell")
    await state.set_state(Trade.waiting_for_quantity)
    await callback.answer()
    await callback.message.answer("Введите количество для продажи:")


@router.message(Trade.waiting_for_quantity)
async def process_trade(message: Message, state: FSMContext):
    try:
        qty = float(message.text)
        if qty <= 0:
            raise ValueError
    except Exception as e:
        logger.info("ERROR:", e)
        await message.answer("❌ Введите корректное число.")
        return
    data = await state.get_data()
    ticker = data["last_ticker"]
    price = float(data["last_price"])
    trade_type = data["trade_type"]
    portfolio_id = data.get("portfolio_id")
    if not portfolio_id:
        await message.answer("Сначала создайте или откройте демо-портфель.",
            reply_markup=kb.login_demo)
        await state.clear()
        return
    portfolio = await rq.get_portfolio(portfolio_id)
    total = qty * price
    if trade_type == "buy":
        if portfolio.cash < total:
            await message.answer("❌ Недостаточно свободных средств.\n\n"
                "Введите количество поменьше:")
            return
        async with session() as s:
            category = await s.scalar(
                select(Category).where(Category.name == "Stocks"))
        await rq.buy_position(portfolio_id, ticker, qty, price, category_id=category.id)
        await rq.update_cash(portfolio_id, portfolio.cash - total)
        await rq.add_transaction(portfolio_id, ticker, qty, price, True)
        await message.answer(f"✅ Куплено: {qty} {ticker} на сумму ${total}",
            reply_markup=kb.login_demo)
        await state.clear()
    else:
        success, msg = await rq.sell_position(portfolio_id, ticker, qty)
        if not success:
            await message.answer(f"❌ {msg}\n"
                f"Введите количество поменьше: ")
            return
        await rq.update_cash(portfolio_id, portfolio.cash + total)
        await rq.add_transaction(portfolio_id, ticker, qty, price, False)
        await message.answer(f"✅ Продано: {qty} акций {ticker} на сумму ${total}",
            reply_markup=kb.login_demo)
        await state.clear()


@router.callback_query(F.data.startswith("sell_"))
async def sell_asset(callback: CallbackQuery, state: FSMContext):
    ticker = callback.data.removeprefix("sell_")
    data = await state.get_data()
    positions = await rq.get_positions(data["portfolio_id"])
    position = next((p for p in positions if p.ticker == ticker), None)
    if not position:
        await callback.message.answer("Актив не найден")
        return
    price = await rq.get_stock_price(ticker)
    if price is None:
        await callback.message.answer("К сожалению, не удалось получить актуальную цену")
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
    await callback.message.answer(f"Сколько акций {ticker} хотите продать?\n\n"
        f"Доступно: {round(available, 4)} шт.", reply_markup=keyboard)


@router.message(SellFlow.waiting_quantity)
async def sell_quantity(message: Message, state: FSMContext):
    try:
        qty = float(message.text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное число.")
        return
    data = await state.get_data()
    ticker = data["sell_ticker"]
    price = await rq.get_stock_price(ticker)
    if price is None:
        await message.answer("К сожалению, не удалось получить актуальную цену")
        return
    success, msg = await rq.sell_position(portfolio_id=data["portfolio_id"],
        ticker=data['sell_ticker'], qty=qty)
    if not success:
        await message.answer(f"❌ {msg}\n"
            "Введите количество поменьше: ")
        return
    portfolio = await rq.get_portfolio(data["portfolio_id"])
    total = qty * price
    await rq.update_cash(data["portfolio_id"], portfolio.cash + total)
    await rq.add_transaction(data["portfolio_id"], data["sell_ticker"], qty, price, False)
    await message.answer(f"✅ Продано: {qty} акицй {data['sell_ticker']}",
        reply_markup=kb.login_demo)
    await state.clear()


@router.callback_query(F.data.startswith("sell%"))
async def sell_percentage(callback, state):
    percent = int(callback.data.removeprefix("sell%"))
    data = await state.get_data()
    positions = await rq.get_positions(data["portfolio_id"])
    position = next((p for p in positions
        if p.ticker == data["sell_ticker"]), None)
    if not position:
        await callback.message.answer("К сожалению, не удалось найти позицию")
        return
    qty = position.quantity*percent/100
    portfolio = await rq.get_portfolio(data["portfolio_id"])
    price = data["sell_price"]
    if not price:
        await callback.message.answer("К сожалению, не удалось получить актуальную цену")
        return
    total = qty * price
    success, msg = await rq.sell_position(portfolio_id=data["portfolio_id"],
        ticker=data["sell_ticker"], qty=qty)
    if success:
        await rq.update_cash(data["portfolio_id"], portfolio.cash+total)
        await rq.add_transaction(data["portfolio_id"], data["sell_ticker"], qty, price, False)
        await callback.message.answer(f"✅ Продано: {percent}% доли акции {data['sell_ticker']}",
            reply_markup=kb.login_demo)
    else:
        await callback.message.answer(msg)