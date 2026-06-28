import asyncio
from datetime import datetime, timezone
import random
import yfinance as yf
import pandas as pd
from sqlalchemy import select
from ProjectDataBase.models import (async_session, Position, MarketPrice,
    HistoricalPrice, StockFundamentals)
from yahooquery import Ticker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func, text
import logging

logger = logging.getLogger("halal")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(levelname)s] %(asctime)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

UPDATE_INTERVAL = 900
CORE_TICKERS = {
    "SPY",
    "VOO",
    "QQQ",
    "VTI",
    "AAPL",
    "MSFT",
    "NVDA"}
KNOWN_FINANCIAL_CURRENCY = {
    "TSM": "TWD",
    "005930.KS": "KRW",
    "2330.TW": "TWD",
    "SSNLF": "KRW"}

async def get_all_tickers():
    async with async_session() as session:
        result = await session.scalars(
            select(Position.ticker).distinct())
        tickers = set(result.all())
        tickers.update({"SPY", "VOO", "QQQ", "VTI"})
        logger.info("ALL TICKERS: %s", sorted(tickers))
        return list(tickers)

def find_interest_income(income):
    if income is None or income.empty:
        return None
    keywords = [
        "interest income",
        "interest income non operating",
        "net interest income",
        "interest and investment income",
        "investment income",
        "interest and dividend income"]
    for idx in income.index:
        row_name = str(idx).lower()
        if not any(k in row_name for k in keywords):
            continue
        try:
            row = income.loc[idx]
            row = pd.to_numeric(row, errors="coerce")
            row = row.dropna()
            if row.empty:
                continue
            return float(row.iloc[0])
        except Exception:
            continue
    return None

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
        async with async_session() as session:
            latest_date = await session.scalar(
                select(func.max(HistoricalPrice.date))
                .where(HistoricalPrice.ticker == ticker))
            stock = yf.Ticker(ticker)
            if latest_date:
                hist = await asyncio.to_thread(
                    lambda: stock.history(start=latest_date))
            else:
                hist = await asyncio.to_thread(
                    lambda: stock.history(period="2y"))
            if hist is None or hist.empty:
                print(f"HISTORY EMPTY: {ticker}")
                return
            rows = []
            for idx, row in hist.iterrows():
                rows.append({
                    "ticker": ticker,
                    "date": idx.date(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),})
            stmt = insert(HistoricalPrice).values(rows)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["ticker", "date"])
            await session.execute(stmt)
            await session.commit()
            result = await session.execute(text("SELECT current_database()"))
            print("UPDATE_HISTORY DB =", result.scalar())
    except Exception as e:
        print(f"HISTORY ERROR {ticker}: {e}")



def get_first_existing(df, keys):
    if df is None or df.empty:
        return None
    for key in keys:
        if key in df.index:
            try:
                return float(df.loc[key].iloc[0])
            except Exception:
                pass
    return None


async def update_fundamentals(ticker, session):
    try:
        logger.info("FUND 1 %s", ticker)
        stock = yf.Ticker(ticker)
        bs = await asyncio.to_thread(lambda: stock.balance_sheet)
        logger.info("FUND 2 %s", ticker)
        income = await asyncio.to_thread(lambda: stock.income_stmt)
        logger.info("FUND 3 %s", ticker)
        total_debt = get_first_existing(bs, ["Total Debt",
            "Current Debt", "Long Term Debt"])
        total_cash = get_first_existing(bs, [
            "Cash And Cash Equivalents", "Cash",
            "Cash Cash Equivalents And Short Term Investments",])
        total_assets = get_first_existing(bs, ["Total Assets"])
        receivables = get_first_existing(bs, ["Net Receivables",
            "Accounts Receivable", "Accounts Receivables",
            "Receivable"])
        revenue = get_first_existing(income, [
            "Total Revenue", "Operating Revenue",
            "Revenue"])
        interest_income = find_interest_income(income)
        if ticker == "AAPL":
            print("INTEREST RESULT:", interest_income)
        modules = await asyncio.to_thread(
            lambda: Ticker(ticker).get_modules([
            "assetProfile",
            "financialData",
            "quoteType"])) or {}
        logger.info("FUND 4 %s", ticker)
        data = modules.get(ticker, {})
        profile = data.get("assetProfile", {})
        financial = data.get("financialData", {})
        quote = data.get("quoteType", {})
        fast = await asyncio.to_thread(lambda: stock.fast_info)
        logger.info("FUND 5 %s", ticker)
        info = await asyncio.to_thread(lambda: stock.info)
        logger.info("FUND 6 %s", ticker)
        financial_currency = (
                financial.get("financialCurrency")
                or info.get("financialCurrency")
                or info.get("currency")
                or fast.get("currency"))
        financial_currency = KNOWN_FINANCIAL_CURRENCY.get(ticker,
            financial_currency)
        logger.info(
            "DB UPDATE %s currency=%s debt=%s cash=%s revenue=%s assets=%s",
            ticker,
            financial_currency,
            total_debt,
            total_cash,
            revenue,
            total_assets)
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
            "revenue": revenue,
            "interest_income": interest_income,
            "financial_currency": financial_currency}
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
            existing.financial_currency = payload["financial_currency"]
            existing.updated_at = datetime.now(timezone.utc)
        else:
            session.add(StockFundamentals(ticker=ticker, **payload))
    except Exception as e:
        await session.rollback()
        print(f"FUNDAMENTALS ERROR {ticker}: {e}")


semaphore = asyncio.Semaphore(5)
async def process_ticker(ticker):
    logger.info("START %s", ticker)
    async with semaphore:
        async with async_session() as session:
            try:
                await update_market_price(ticker, session)
                logger.info("PRICE DONE %s", ticker)
                await update_fundamentals(ticker, session)
                logger.info("FUND DONE %s", ticker)
                if ticker in CORE_TICKERS:
                    await update_history(ticker)
                elif random.random() < 0.1:
                    await update_history(ticker)
                await session.commit()
                logger.info("COMMIT DONE %s", ticker)
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