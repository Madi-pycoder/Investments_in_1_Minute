from sqlalchemy import select
from ProjectDataBase.market_data_worker import update_market_price, update_history, update_fundamentals
from ProjectDataBase.models import (
    async_session,
    MarketPrice,
    HistoricalPrice,
    StockFundamentals,)
from datetime import datetime, timedelta, timezone
import numpy as np
def ensure_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def get_cached_price(ticker):
    async with async_session() as session:
        market = await session.scalar(
            select(MarketPrice).where(
                MarketPrice.ticker == ticker))
        market_updated = ensure_utc(
            market.updated_at
        ) if market and market.updated_at else None
        is_stale = (
            not market
            or not market_updated
            or datetime.now(timezone.utc) - market_updated > timedelta(minutes=20))
        if is_stale:
            try:
                await update_market_price(ticker, session)
                await session.commit()
            except Exception as e:
                await session.rollback()
                print("UPDATE PRICE ERROR:", e)
            market = await session.scalar(
                select(MarketPrice).where(
                    MarketPrice.ticker == ticker))
        if not market:
            return {"error": "Ticker not found"}
        return {
            "ticker": ticker,
            "price": market.price or 0,
            "volume": market.volume or 0,
            "market_cap": market.market_cap or 0,
            "pe": market.pe_ratio or 0}


async def get_bulk_prices(tickers):
    async with async_session() as session:
        result = await session.scalars(
            select(MarketPrice)
            .where(MarketPrice.ticker.in_(tickers)))
        rows = result.all()
    return {
        r.ticker: r.price
        for r in rows
        if r.price}

async def get_price_history(ticker):
    async with async_session() as session:
        result = await session.scalars(
            select(HistoricalPrice)
            .where(HistoricalPrice.ticker == ticker)
            .order_by(HistoricalPrice.date))
        return result.all()

async def get_cached_fundamentals(ticker):
    async with async_session() as session:
        data = await session.scalar(
            select(StockFundamentals).where(
                StockFundamentals.ticker == ticker))
        data_updated = ensure_utc(data.updated_at) if data else None
        is_stale = (
            not data
            or not data_updated
            or datetime.now(timezone.utc) - data_updated > timedelta(days=7))
        if is_stale:
            try:
                await update_fundamentals(ticker, session)
                await session.commit()
            except Exception as e:
                print("FUNDAMENTALS UPDATE ERROR:", e)
            data = await session.scalar(
                select(StockFundamentals).where(
                    StockFundamentals.ticker == ticker))
        return data


async def calculate_volatility_cached(ticker):
    hist = await get_price_history(ticker)
    if len(hist) < 2:
        await update_history(ticker)
        hist = await get_price_history(ticker)
    if len(hist) < 2:
        return 0
    closes = [
        h.close
        for h in hist
        if h.close is not None]
    if len(closes) < 2:
        return 0
    returns = np.diff(closes) / closes[:-1]
    volatility = (
        np.std(returns)
        * np.sqrt(252)
        * 100)
    return round(volatility, 2)


async def calculate_drawdown_cached(ticker):
    hist = await get_price_history(ticker)
    if not hist:
        await update_history(ticker)
        hist = await get_price_history(ticker)
    if not hist:
        return 0
    closes = [
        h.close
        for h in hist
        if h.close is not None]
    if not closes:
        return 0
    peak = closes[0]
    max_dd = 0
    for c in closes:
        if c > peak:
            peak = c
        if peak == 0:
            continue
        dd = (c - peak) / peak
        max_dd = min(max_dd, dd)
    return round(max_dd * 100, 2)
