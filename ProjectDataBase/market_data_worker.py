import asyncio
from datetime import datetime, timezone
import random
import yfinance as yf
from sqlalchemy import select
from ProjectDataBase.models import (async_session, Position, MarketPrice,
                                    HistoricalPrice,
                                    StockFundamentals)
from yahooquery import Ticker

UPDATE_INTERVAL = 900

async def get_all_tickers():
    async with async_session() as session:
        result = await session.scalars(
            select(Position.ticker).distinct())
        return result.all()

async def update_market_price(ticker, session):
    try:
        stock = yf.Ticker(ticker)
        fast = await asyncio.to_thread(lambda: stock.fast_info) or {}
        price = fast.get("lastPrice") or fast.get("currentPrice")
        if price is None:
            hist = await asyncio.to_thread(lambda: stock.history(period="1d"))
            if hist is not None and not hist.empty:
                price = float(hist["Close"].iloc[-1])
        if price is None:
            print(f"SKIP {ticker}: no price data")
            return
        existing = await session.scalar(
        select(MarketPrice).where(MarketPrice.ticker == ticker))
        payload = {
            "price": float(price),
            "volume": float(fast.get("volume") or 0),
            "market_cap": float(fast.get("marketCap") or 0),
            "pe_ratio": (
                float(fast["trailingPE"])
                if fast.get("trailingPE") is not None else None),}
        if existing:
            existing.price = payload["price"]
            existing.volume = payload["volume"]
            existing.market_cap = payload["market_cap"]
            existing.pe_ratio = payload["pe_ratio"]
            existing.updated_at = datetime.now(timezone.utc)
        else:
            session.add(MarketPrice(ticker=ticker, **payload))
    except Exception as e:
        await session.rollback()
        print(f"PRICE ERROR {ticker}: {e}")


async def update_history(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = await asyncio.to_thread(lambda: stock.history(period="6mo"))
        if hist is None or hist.empty:
            return
        async with async_session() as session:
            existing_dates = await session.scalars(
                select(HistoricalPrice.date).where(HistoricalPrice.ticker == ticker))
            existing_dates = set(existing_dates.all())
            new_rows = []
            for idx, row in hist.iterrows():
                date = idx.date()
                if date in existing_dates:
                    continue
                new_rows.append(
                    HistoricalPrice(
                        ticker=ticker,
                        date=date,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row["Volume"]),))
            if new_rows:
                session.add_all(new_rows)
                await session.commit()
    except Exception as e:
        print(f"HISTORY ERROR {ticker}: {e}")


async def update_fundamentals(ticker, session):
    try:
        stock = yf.Ticker(ticker)
        bs = await asyncio.to_thread(
            lambda: stock.balance_sheet)
        receivables = None
        total_debt = None
        total_cash = None
        total_assets = None
        if bs is not None and not bs.empty:
            for key in ["Net Receivables",
                "Accounts Receivable"]:
                if key in bs.index:
                    try:
                        receivables = float(bs.loc[key].iloc[0])
                        break
                    except Exception:
                        pass
            if "Total Debt" in bs.index:
                try:
                    total_debt = float(bs.loc["Total Debt"].iloc[0])
                except Exception:
                    pass
            for key in [
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments"]:
                if key in bs.index:
                    try:
                        total_cash = float(bs.loc[key].iloc[0])
                        break
                    except Exception:
                        pass
            if "Total Assets" in bs.index:
                try:
                    total_assets = float(bs.loc["Total Assets"].iloc[0])
                except Exception:
                    pass
        modules = await asyncio.to_thread(
            lambda: Ticker(ticker).get_modules([
            "assetProfile",
            "financialData",
            "quoteType"])) or {}
        data = modules.get(ticker, {})
        profile = data.get("assetProfile", {})
        financial = data.get("financialData", {})
        quote = data.get("quoteType", {})
        existing = await session.scalar(
            select(StockFundamentals).where(StockFundamentals.ticker == ticker))
        payload = {
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "market_cap": financial.get("marketCap"),
            "quote_type": quote.get("quoteType"),
            "total_debt": total_debt,
            "total_cash": total_cash,
            "total_assets": total_assets,
            "receivables": receivables,
            "revenue": financial.get("totalRevenue"),
            "interest_income": financial.get("interestIncome")}
        if existing:
            existing.sector = payload["sector"]
            existing.industry = payload["industry"]
            existing.market_cap = payload["market_cap"]
            existing.quote_type = payload["quote_type"]
            existing.total_debt = payload["total_debt"]
            existing.total_cash = payload["total_cash"]
            existing.total_assets = payload["total_assets"]
            existing.receivables = payload["receivables"]
            existing.revenue = payload["revenue"]
            existing.interest_income = payload["interest_income"]
            existing.updated_at = datetime.now(timezone.utc)
        else:
            session.add(StockFundamentals(ticker=ticker, **payload))
    except Exception as e:
        await session.rollback()
        print(f"FUNDAMENTALS ERROR {ticker}: {e}")


semaphore = asyncio.Semaphore(5)
async def process_ticker(ticker):
    async with semaphore:
        async with async_session() as session:
            try:
                await update_market_price(ticker, session)
                await update_fundamentals(ticker, session)
                if random.random() < 0.1:
                    await update_history(ticker)
                await session.commit()
            except Exception as e:
                print(f"ERROR {ticker}: {e}")


async def market_worker():
    while True:
        try:
            tickers = await get_all_tickers()
            tasks = [
                process_ticker(t)
                for t in tickers]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print("WORKER ERROR:", e)
        await asyncio.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    asyncio.run(market_worker())