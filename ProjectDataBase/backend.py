import time
import asyncio
import yfinance as yf
import logging
from sqlalchemy import select, delete, update
from MainEngines.auto_invest_engine import get_cached_metrics
from ProjectDataBase.cache import portfolio_data_cache, diagnosis_cache, portfolio_cache, PORTFOLIO_VIEW_CACHE
from ProjectDataBase.models import (Owner, Demo, Portfolio, Position, MarketPrice,
    Transaction, Goal, async_session, PortfolioSettings)

logger = logging.getLogger(__name__)

def make_portfolio_cache_key(positions):
    normalized = sorted(
        [(p["ticker"], round(p["weight"], 4))for p in positions])
    return tuple(normalized)



def get_portfolio_data_cached(portfolio_id):
    item = portfolio_data_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > 30:
        return None
    return item["data"]

async def preload_diagnosis(portfolio_id, data):
    try:
        metrics = await get_cached_metrics(portfolio_id, data)
        diagnosis_cache[portfolio_id] = {
            "data": metrics,
            "ts": time.time()}
    except Exception as e:
        logger.info("preload_diagnosis ERROR:", e)

def get_diagnosis_cached(portfolio_id):
    item = diagnosis_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > 60:
        return None
    return item["data"]

async def set_user(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(
            select(Owner).where(Owner.tg_id == tg_id))
        if not user:
            session.add(Owner(tg_id=tg_id))
            await session.commit()

async def create_demo_portfolio(tg_id: int, demo_name: str):
    async with async_session() as session:
        owner = await session.scalar(
            select(Owner).where(Owner.tg_id == tg_id))
        if not owner:
            return None
        portfolio = Portfolio(
            owner_id=owner.id,
            cash=10000.0,
            total_value = 10000.0)
        session.add(portfolio)
        await session.flush()
        demo = Demo(
            name=demo_name,
            portfolio_id=portfolio.id)
        session.add(demo)
        await session.commit()
        return portfolio.id

async def buy_position(portfolio_id, ticker, qty, price, category_id):
    async with async_session() as session:
        if category_id is None:
            raise ValueError(f"category_id is None for {ticker}")
        existing = await session.scalar(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.ticker == ticker))
        if existing:
            total_qty = existing.quantity + qty
            new_avg = (
                (existing.quantity *
                     existing.average_price +
                        qty * price)/ total_qty)
            existing.quantity = total_qty
            existing.average_price = new_avg
        else:
            session.add(
                Position(
                    portfolio_id=portfolio_id,
                    ticker=ticker,
                    quantity=qty,
                    average_price=price,
                    category_id=category_id))
        await session.commit()
        await session.commit()
        PORTFOLIO_VIEW_CACHE.pop(portfolio_id, None)
        portfolio_cache.pop(portfolio_id, None)
        portfolio_data_cache.pop(portfolio_id, None)
        diagnosis_cache.pop(portfolio_id, None)
        await recalculate_portfolio_value(portfolio_id)


async def sell_position(portfolio_id, ticker, qty):
    async with async_session() as session:
        position = await session.scalar(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.ticker == ticker))
        if not position:
            return False, "Этого актива нет в портфеле"
        EPS = 0.000001
        if position.quantity + EPS < qty:
            return False, ("Недостаточно активов для продажи.\n\n"
                "Проверьте количество в портфеле и попробуйте снова.")
        position.quantity -= qty
        if position.quantity <= EPS:
            await session.delete(position)
        await session.commit()
        PORTFOLIO_VIEW_CACHE.pop(portfolio_id, None)
        portfolio_cache.pop(portfolio_id, None)
        portfolio_data_cache.pop(portfolio_id, None)
        diagnosis_cache.pop(portfolio_id, None)
        await recalculate_portfolio_value(portfolio_id)
        return True, "Продажа выполнена"


async def add_transaction(portfolio_id, ticker, qty, price, is_buy):
    async with async_session() as session:
        tr = Transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=qty,
            price=price,
            is_buy=is_buy)
        session.add(tr)
        await session.commit()


async def get_portfolio(portfolio_id):
    async with async_session() as session:
        return await session.scalar(
            select(Portfolio).where(Portfolio.id == portfolio_id))


async def get_positions(portfolio_id):
    async with async_session() as session:
        result = await session.scalars(
            select(Position).where(Position.portfolio_id == portfolio_id))
        return result.all()


async def get_user_portfolios(tg_id: int):
    async with async_session() as session:
        owner = await session.scalar(
            select(Owner).where(Owner.tg_id == tg_id))
        if not owner:
            return []
        result = await session.execute(
            select(Demo, Portfolio)
            .join(Portfolio, Demo.portfolio_id == Portfolio.id)
            .where(Portfolio.owner_id == owner.id))
        return result.all()


async def login_demo_portfolio(tg_id: int, demo_name: str):
    async with async_session() as session:
        owner = await session.scalar(
            select(Owner).where(Owner.tg_id == tg_id))
        if not owner:
            return None, "Пользователь не найден"
        demo = await session.scalar(
            select(Demo).where(Demo.name == demo_name))
        if not demo:
            return None, "Портфель не найден"
        portfolio = await session.scalar(
            select(Portfolio).where(Portfolio.id == demo.portfolio_id))
        if not portfolio:
            return None, ("Портфель не найден.\n\n"
                "Попробуйте открыть другой портфель или создать новый.")
        return portfolio, "Успешный вход"


async def update_cash(portfolio_id: int, new_cash: float):
    async with async_session() as session:
        portfolio = await session.get(Portfolio, portfolio_id)
        portfolio.cash = new_cash
        await recalculate_portfolio_value(portfolio_id)
        await session.commit()
        diagnosis_cache.pop(portfolio_id, None)


async def delete_portfolio(portfolio_id):
    async with async_session() as session:
        await session.execute(
            delete(Demo).where(Demo.portfolio_id == portfolio_id))
        await session.execute(
            delete(Position).where(Position.portfolio_id == portfolio_id))
        await session.execute(
            delete(Transaction).where(Transaction.portfolio_id == portfolio_id))
        await session.execute(
            delete(Goal).where(Goal.portfolio_id == portfolio_id))
        await session.execute(
            delete(PortfolioSettings).where(PortfolioSettings.portfolio_id == portfolio_id))
        await session.execute(
            delete(Portfolio).where(Portfolio.id == portfolio_id))
        await session.commit()



async def execute_rebalance(portfolio_id, trades):
    async with async_session() as session:
        portfolio = await session.get(Portfolio, portfolio_id)
        if not portfolio:
            return False, "Портфель не найден"
        tickers = [t["ticker"] for t in trades]
        result = await session.execute(
            select(MarketPrice.ticker, MarketPrice.price).where(
                MarketPrice.ticker.in_(tickers)))
        prices_dict = {ticker: price
            for ticker, price in  result.all()}
        executed_trades = []
        for t in trades:
            ticker = t["ticker"]
            amount = t["amount"]
            action = t["action"]
            price = prices_dict.get(ticker)
            if price is None:
                continue
            qty = amount / price
            if action == "BUY":
                if portfolio.cash < amount:
                    continue
                portfolio.cash -= amount
                existing = await session.scalar(
                    select(Position).where(
                        Position.portfolio_id == portfolio_id,
                        Position.ticker == ticker))
                if existing:
                    total_qty = existing.quantity + qty
                    new_avg = (
                        (existing.quantity * existing.average_price + qty * price)/total_qty)
                    existing.quantity = total_qty
                    existing.average_price = new_avg
                else:
                    session.add(Position(
                        portfolio_id=portfolio_id,
                        ticker=ticker,
                        quantity=qty,
                        average_price=price,
                        category_id=1))
                session.add(Transaction(
                    portfolio_id=portfolio_id,
                    ticker=ticker,
                    quantity=qty,
                    price=price,
                    is_buy=True))
                executed_trades.append(f"BUY {ticker} ${round(amount, 2)}")
            elif action == "SELL":
                position = await session.scalar(
                    select(Position).where(
                        Position.portfolio_id == portfolio_id,
                        Position.ticker == ticker))
                if not position:
                    continue
                sell_qty = min(position.quantity, qty)
                portfolio.cash += sell_qty * price
                position.quantity -= sell_qty
                if position.quantity <= 0:
                    await session.delete(position)
                executed_trades.append(f"SELL {ticker} ${round(sell_qty * price, 2)}")
                await recalculate_portfolio_value(portfolio_id)
                session.add(Transaction(
                    portfolio_id=portfolio_id,
                    ticker=ticker,
                    quantity=qty,
                    price=price,
                    is_buy=False))
        await session.commit()
        PORTFOLIO_VIEW_CACHE.pop(portfolio_id, None)
        portfolio_cache.pop(portfolio_id, None)
        portfolio_data_cache.pop(portfolio_id, None)
        diagnosis_cache.pop(portfolio_id, None)
        if not executed_trades:
            return False, "Не удалось выполнить сделки", []
        await recalculate_portfolio_value(portfolio_id)
        return True, len(executed_trades), executed_trades


async def get_goals(portfolio_id):
    async with async_session() as session:
        result = await session.scalars(
            select(Goal).where(Goal.portfolio_id == portfolio_id))
        return [g.__dict__ for g in result.all()]


async def add_goal(goal_data):
    async with async_session() as session:
        goal = Goal(**goal_data)
        session.add(goal)
        await session.commit()


async def update_goal(goal_id: int, **kwargs):
    async with async_session() as session:
        await session.execute(
            update(Goal)
            .where(Goal.id == goal_id)
            .values(**kwargs))
        await session.commit()

async def delete_goal(goal_id: int):
    async with async_session() as session:
        await session.execute(
            delete(Goal).where(Goal.id == goal_id))
        await session.commit()

async def add_cash(portfolio_id: int, amount: float):
    async with async_session() as session:
        portfolio = await session.get(Portfolio, portfolio_id)
        if not portfolio:
            return False
        portfolio.cash += amount
        await session.commit()
        await recalculate_portfolio_value(portfolio_id)
        diagnosis_cache.pop(portfolio_id, None)
        return True


async def get_stock_price(ticker):
    def _load():
        stock = yf.Ticker(ticker)
        price = stock.fast_info.get("lastPrice")
        if price is None:
            info = stock.info
            price = info.get("currentPrice")
        return price
    try:
        return await asyncio.to_thread(_load)
    except Exception:
        return None


async def deposit_monthly_budget(portfolio_id, amount):
    async with async_session() as session:
        portfolio = await session.get(Portfolio, portfolio_id)
        portfolio.cash += amount
        await session.commit()
        return True


async def recalculate_portfolio_value(portfolio_id):
    async with async_session() as session:
        portfolio = await session.get(Portfolio, portfolio_id)
        positions = (await session.scalars(
            select(Position).where(
                Position.portfolio_id == portfolio_id))).all()
        total = portfolio.cash
        for pos in positions:
            price = await session.scalar(
                select(MarketPrice.price)
                .where(MarketPrice.ticker == pos.ticker))
            if price:
                total += pos.quantity * price
        portfolio.total_value = round(total, 2)
        await session.commit()