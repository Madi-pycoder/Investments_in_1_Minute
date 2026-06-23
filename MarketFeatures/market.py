from datetime import datetime, timedelta, timezone
from io import StringIO
from yahooquery import Ticker
from ProjectDataBase.cache import (FX_CACHE, STOCKS_CACHE,
    STOCK_INFO_CACHE, STOCK_INFO_TTL, get_cached, set_cached)
from ProjectDataBase.market_data_worker import get_first_existing, find_interest_income
from ProjectDataBase.models import async_session, StockFundamentals
from sqlalchemy import select
import yfinance as yf
import requests
import pandas as pd
import asyncio
import math
import traceback

SP500_TOP = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
    "BRK-B", "LLY", "TSLA", "AVGO", "JPM", "UNH",
    "V", "XOM", "MA", "PG", "COST", "HD", "MRK",
    "ABBV", "ADBE", "CRM", "PEP", "KO", "AMD",
    "NFLX", "TMO", "LIN", "MCD", "INTC"]
NASDAQ_PROXY = [
    "NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META",
    "AVGO", "WMT", "MU", "TMUS", "LRCX", "AMD", "NFLX",
    "CMCSA", "QCOM", "INTU"]
def clean_number(value):
    if value is None:
        return None
    try:
        value = float(value)
        if math.isnan(value):
            return None
        if math.isinf(value):
            return None
        return value
    except Exception:
        return None


def safe_close(hist):
    if hist is None or hist.empty:
        return None
    return hist["Close"].iloc[-1]

async def run_blocking(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args))

def last_valid_close(hist):
    try:
        return float(hist["Close"].dropna().iloc[-1])
    except:
        return None

async def get_prices_only(tickers):
    data = await asyncio.to_thread(
        yf.download,
        tickers=tickers,
        period="1d",
        interval="1d",
        progress=False,
        auto_adjust=True,
        threads=True)
    prices = {}
    for t in tickers:
        try:
            prices[t] = float(data["Close"][t].dropna().iloc[-1])
        except Exception:
            continue
    return prices

def get_price_fallback(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        r = requests.get(url, timeout=5)
        data = r.json()
        result = data.get("chart", {}).get("result")
        if not result:
            return None
        return float(result[0]["meta"].get("regularMarketPrice"))
    except Exception as e:
        print("ERROR:", e)
        return None


async def get_index_proxy(ticker: str):
    ticker = ticker.upper()
    if ticker in ["SPY", "VOO", "IVV", "SPLG"]:
        return SP500_TOP
    if ticker in ["QQQ"]:
        return NASDAQ_PROXY
    etf_type = await detect_etf_type(ticker)
    if etf_type == "vanguard":
        return SP500_TOP
    if etf_type == "invesco":
        return NASDAQ_PROXY
    universe = SP500_TOP + NASDAQ_PROXY
    return universe[:30]



async def get_fx_rate(from_currency, to_currency="USD"):
    if not from_currency or from_currency == to_currency:
        return 1.0
    key = f"{from_currency}_{to_currency}"
    if key in FX_CACHE:
        return FX_CACHE[key]
    try:
        pair = f"{from_currency}{to_currency}=X"
        fx = yf.Ticker(pair)
        hist = await asyncio.to_thread(
            fx.history,
            period="1d")
        if hist is None or hist.empty:
            return 1.0
        rate = float(hist["Close"].iloc[-1])
        FX_CACHE[key] = rate
        return rate
    except Exception as e:
        print("FX ERROR:", e)
        return 1.0



async def ensure_fundamentals_exist(ticker: str, force_refresh: bool=False):
    async with async_session() as session:
        row = await session.scalar(
            select(StockFundamentals)
            .where(StockFundamentals.ticker == ticker))
        if row and not force_refresh:
            return row
        print(f"[AUTO LOAD] {ticker}")
        stock = yf.Ticker(ticker)
        bs = await asyncio.to_thread(lambda: stock.balance_sheet)
        income = await asyncio.to_thread(lambda: stock.income_stmt)
        total_debt = get_first_existing(bs, ["Total Debt", "Current Debt",
            "Long Term Debt"])
        total_cash = get_first_existing(bs, ["Cash And Cash Equivalents",
            "Cash", "Cash Cash Equivalents And Short Term Investments"])
        total_assets = get_first_existing(bs, ["Total Assets"])
        receivables = get_first_existing(bs, ["Net Receivables",
            "Accounts Receivable", "Accounts Receivables"])
        revenue = get_first_existing(income, ["Total Revenue",
            "Operating Revenue", "Revenue"])
        interest_income = find_interest_income(income)
        modules = await asyncio.to_thread(
            lambda: Ticker(ticker).get_modules([
                "assetProfile",
                "financialData",
                "quoteType"])) or {}
        data = modules.get(ticker, {})
        profile = data.get("assetProfile", {})
        financial = data.get("financialData", {})
        quote = data.get("quoteType", {})
        row = StockFundamentals(
            ticker=ticker,
            sector=profile.get("sector"),
            industry=profile.get("industry"),
            market_cap=financial.get("marketCap"),
            quote_type=quote.get("quoteType"),
            total_debt=total_debt,
            total_cash=total_cash,
            total_assets=total_assets,
            receivables=receivables,
            revenue=revenue,
            interest_income=interest_income,
            updated_at=datetime.now(timezone.utc))
        session.add(row)
        await session.commit()
        return row






async def get_stock_info(ticker: str):
    ticker = ticker.upper()
    cached = get_cached(STOCK_INFO_CACHE, ticker, STOCK_INFO_TTL)
    if cached:
        return cached
    try:
        print(f"FETCHING {ticker}")
        stock = yf.Ticker(ticker)
        hist = await asyncio.to_thread(stock.history, period="5y")
        if hist is None or hist.empty:
            return {"error": f"❌ Тикер {ticker} не найден"}
        print(hist.tail())
        print("EMPTY:", hist.empty)
        price = None
        if hist is not None and not hist.empty:
            price = last_valid_close(hist)
        if price is None:
            price = get_price_fallback(ticker)
        if price is None:
            return {"error": "Не удалось получить цену актива"}
        close = safe_close(hist)
        if close is None:
            return {"error": "Недостаточно исторических данных"}
        def pct(period):
            try:
                if len(hist) <= period:
                    return None
                close_series = hist["Close"].dropna()
                current = close_series.iloc[-1]
                past = close_series.iloc[-(period+1)]
                return round((current - past)/past * 100, 2)
            except Exception as e:
                print("ERROR:", e)
                return None
        growth = {
            "1D": pct(1),
            "5D": pct(5),
            "1M": pct(22),
            "6M": pct(126),
            "1Y": pct(252),
            "5Y": pct(len(hist)-1)}
        modules = await asyncio.to_thread(
            lambda: Ticker(ticker).get_modules([
                "assetProfile",
                "financialData",
                "defaultKeyStatistics",
                "calendarEvents",
                "price",
                "summaryDetail"]))
        data = modules.get(ticker, {})
        profile = data.get("assetProfile", {})
        financial = data.get("financialData", {})
        stats = data.get("defaultKeyStatistics", {})
        calendar = data.get("calendarEvents", {})
        price_data = data.get("price", {})
        summary = data.get("summaryDetail", {})
        ed = calendar.get("earningsDate")
        async with async_session() as session:
            fundamentals = await session.scalar(
                select(StockFundamentals)
                .where(StockFundamentals.ticker == ticker))
            if fundamentals is None:
                fundamentals = await ensure_fundamentals_exist(ticker, force_refresh=True)
            need_refresh = (
                fundamentals is None or fundamentals.updated_at is None
                or (datetime.now(timezone.utc) - fundamentals.updated_at)
                > timedelta(days=30))
            if need_refresh:
                fundamentals = await ensure_fundamentals_exist(ticker, force_refresh=True)
            receivables = (
                fundamentals.receivables
                if fundamentals else None)
            total_debt = (
                fundamentals.total_debt
                if fundamentals else None)
            total_cash = (
                fundamentals.total_cash
                if fundamentals else None)
            total_assets = (
                fundamentals.total_assets
                if fundamentals else None)
            revenue = (
                fundamentals.revenue
                if fundamentals else None)
            interest_income = (
                fundamentals.interest_income
                if fundamentals else None)
            financials_updated_at = (
                fundamentals.updated_at
                if fundamentals else None)
        if isinstance(ed, list):
            ed = ed[0]
        dte = financial.get("debtToEquity")
        market_cap = (
                financial.get("marketCap")
                or price_data.get("marketCap")
                or stats.get("marketCap")
                or stock.fast_info.get("market_cap"))
        if market_cap is None:
            market_cap = fundamentals.market_cap
        print("MARKET CAP:", market_cap)
        print("TOTAL CASH:", total_cash)
        print("TOTAL DEBT:", total_debt)
        print("CURRENCY:", price_data.get("currency"))
        print("FINANCIAL CURRENCY:", financial.get("financialCurrency"))
        print("DB INTEREST:", interest_income)
        print("DB REVENUE:", revenue)
        result = {
            "name": price_data.get("shortName"),
            "ticker": ticker.upper(),
            "debt_to_equity": dte / 100 if dte else None,
            "pe": summary.get("trailingPE"),
            "eps": summary.get("trailingEps"),
            "market_cap": clean_number(financial.get("marketCap")
                or price_data.get("marketCap")
                or stats.get("marketCap")),
            "industry": profile.get("industry"),
            "sector": profile.get("sector"),
            "dividends": stats.get("dividendRate"),
            "earnings_date": ed,
            "price": float(price),
            "growth": growth,
            "receivables": clean_number(receivables),
            "total_debt": clean_number(total_debt),
            "total_cash": clean_number(total_cash),
            "total_assets": clean_number(total_assets),
            "revenue": clean_number(revenue),
            "interest_income": clean_number(interest_income),
            "financials_updated_at": financials_updated_at,
            "ebitda": clean_number(financial.get("ebitda"))}
        set_cached(STOCK_INFO_CACHE, ticker, result)
        return result
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

async def get_etf_info(ticker: str):
    try:
        etf = yf.Ticker(ticker)
        hist = await asyncio.to_thread(etf.history, period="5y")
        if hist is None or hist.empty:
            return {
                "error": f"❌ Тикер {ticker} не найден"}
        if hist is None or hist.empty:
            return {"error": "Не удалось получить рыночные данные"}
        price = None
        if hist is not None and not hist.empty:
            price = last_valid_close(hist)
        if price is None:
            price = get_price_fallback(ticker)
        if price is None:
            return {"error": "Не удалось получить цену актива"}
        def pct(period):
            try:
                return round(
                    (price - hist["Close"].iloc[-period])
                    / hist["Close"].iloc[-period] * 100, 2)
            except Exception as e:
                print("ERROR:", e)
                return None
        growth = {
            "1D": pct(1),
            "5D": pct(5),
            "1M": pct(22),
            "6M": pct(126),
            "1Y": pct(252),
            "5Y": pct(len(hist)-1)}
        t = Ticker(ticker)
        modules = await asyncio.to_thread(
            lambda: Ticker(ticker).get_modules([
            "fundProfile",
            "summaryDetail",
            "defaultKeyStatistics",
            "price"])) or {}
        data = modules.get(ticker, {})
        fund = data.get("fundProfile", {})
        summary = data.get("summaryDetail", {})
        stats = data.get("defaultKeyStatistics", {})
        price_data = data.get("price", {})
        name = (fund.get("shortName") or price_data.get("shortName") or ticker)
        return {
            "name": name,
            "ticker": ticker.upper(),
            "nav": stats.get("navPrice"),
            "net_assets": stats.get("totalAssets"),
            "pe": summary.get("trailingPE"),
            "expense": summary.get("expenseRatio"),
            "price": float(price),
            "growth": growth}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


async def fetch_chunk(chunk, retries=3):
    for attempt in range(retries):
        try:
            modules = await asyncio.to_thread(
                lambda: Ticker(chunk).get_modules([
                "assetProfile",
                 "financialData",
                 "defaultKeyStatistics"])) or {}
            result = {}
            async with async_session() as session:
                fundamentals_rows = await session.scalars(
                    select(StockFundamentals)
                    .where(StockFundamentals.ticker.in_(chunk)))
                fundamentals_map = {
                    row.ticker.upper(): row
                    for row in fundamentals_rows}
            for ticker in chunk:
                data = modules.get(ticker, {}) or {}
                profile = data.get("assetProfile", {})
                financial = data.get("financialData", {})
                stats = data.get("defaultKeyStatistics", {})
                db_row = fundamentals_map.get(ticker.upper())
                result[ticker] = {
                    "industry": profile.get("industry"),
                    "sector": profile.get("sector"),
                    "market_cap": financial.get("marketCap") or stats.get("marketCap"),
                    "revenue": db_row.revenue if db_row else None,
                    "interest_income": db_row.interest_income if db_row else None,
                    "total_debt": db_row.total_debt if db_row else None,
                    "total_cash": db_row.total_cash if db_row else None,
                    "total_assets": db_row.total_assets if db_row else None,
                    "receivables": db_row.receivables if db_row else None,
                    "dividends": financial.get("dividendYield")}
            STOCKS_CACHE.update(result)
            return result
        except Exception as e:
            print(f"Retry {attempt+1} for chunk failed:", e)
            await asyncio.sleep(1.5 * (attempt + 1))
        for ticker in chunk:
            if ticker not in STOCKS_CACHE:
                STOCKS_CACHE[ticker] = {
                    "industry": None,
                    "sector": None,
                    "market_cap": None,
                    "total_assets": None,
                    "total_debt": None,
                    "total_cash": None,
                    "receivables": None,}
    print("Chunk полностью упал:", chunk)
    return {}

semaphore = asyncio.Semaphore(2)

async def fetch_chunk_limited(chunk):
    missing = [t for t in chunk if t not in STOCKS_CACHE]
    if not missing:
        return {t: STOCKS_CACHE[t] for t in chunk}
    async with semaphore:
        return await fetch_chunk(chunk)

async def get_stocks_batch(tickers):
    chunk_size = 50
    chunks = [tickers[i:i+chunk_size] for i in range(0, len(tickers), chunk_size)]
    tasks = [fetch_chunk_limited(chunk) for chunk in chunks]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    result = {}
    for r in all_results:
        if isinstance(r, Exception):
            print("Chunk error:", r)
            continue
        result.update(r)
    if len(result) == 0:
        print("⚠️ Yahoo полностью упал → fallback")
        return {
            t: {
                "industry": None,
                "sector": None,
                "market_cap": None,
                "total_assets": None,
                "total_debt": None,
                "total_cash": None,
                "receivables": None}
            for t in tickers}
    final = {}
    for t in tickers:
        if t in result:
            final[t] = result[t]
        elif t in STOCKS_CACHE:
            final[t] = STOCKS_CACHE[t]
        else:
            final[t] = {
                "industry": None,
                "sector": None,
                "market_cap": None,
                "total_assets": None,
                "total_debt": None,
                "total_cash": None,
                "receivables": None}
    return final


async def detect_etf_type(ticker):
    try:
        t = Ticker(ticker)
        data = t.get_modules("fundProfile")
        if data is None or ticker not in data:
            return None
        fund = data[ticker].get("fundProfile", {})
        if not isinstance(fund, dict):
            return None
        category = str(fund.get("categoryName", "")).lower()
        family = str(fund.get("family", "")).lower()
        if "vanguard" in family:
            return "vanguard"
        if "ishares" in family or "blackrock" in family:
            return "blackrock"
        if "spdr" in family:
            return "spdr"
        if "invesco" in family:
            return "invesco"
        if "wahed" in family or "shariah" in category:
            return "shariah"
        return "generic"
    except Exception as e:
        print("detect_etf_type error:", e)
        return None

def validate_and_normalize(holdings):
    if holdings is None or len(holdings) == 0:
        return None
    total = sum(h.get("weight", 0) for h in holdings)
    if total <= 0:
        return None
    return [
        {"ticker": h["ticker"], "weight": h["weight"] / total}
        for h in holdings
        if h.get("ticker") and h.get("weight") is not None]

async def load_yahoo_full_holdings(ticker):
    try:
        t = Ticker(ticker)
        data = t.get_modules("topHoldings")
        if data is None or ticker not in data:
            return None
        holdings = data[ticker].get("holdings")
        if holdings is None or len(holdings) == 0:
            return None
        result = []
        for r in holdings:
            symbol = r.get("symbol")
            weight = r.get("holdingPercent")
            if symbol and weight:
                result.append({
                    "ticker": symbol.upper(),
                    "weight": float(weight)})
        print("Yahoo FULL loaded:", len(result))
        return result if len(result) > 0 else None
    except Exception as e:
        print("Yahoo FULL error:", e)
        return None

async def load_shariah_holdings(ticker):
    sources = [
        f"https://funds.wahedinvest.com/{ticker}/holdings.csv",
        f"https://www.sp-funds.com/wp-content/uploads/{ticker}-holdings.csv",
        f"https://cdn.sp-funds.com/{ticker}-holdings.csv",]
    for url in sources:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
            df = pd.read_csv(StringIO(r.text))
            ticker_col = next((c for c in df.columns if "ticker" in c.lower()), None)
            weight_col = next((c for c in df.columns if "weight" in c.lower()), None)
            if not ticker_col or not weight_col:
                continue
            result = [
                {"ticker": str(row[ticker_col]).upper(),
                "weight": float(row[weight_col]) / (100 if df[weight_col].max() > 1 else 1)}
                for _, row in df.iterrows()
                if row[ticker_col] and row[weight_col]]
            if result:
                print("Shariah loaded:", len(result))
                return result
        except Exception as e:
            print(f"Shariah loader error ({url}):", e)
            continue
    return None

async def load_universal_fallback(ticker):
    try:
        t = Ticker(ticker)
        data = t.get_modules("topHoldings")
        if data is None or ticker not in data:
            return None
        holdings = data[ticker].get("holdings")
        if holdings is None or len(holdings) == 0:
            return None
        n = len(holdings)
        result = []
        for h in holdings:
            symbol = h.get("symbol")
            if symbol:
                result.append({
                    "ticker": symbol.upper(),
                    "weight": 1 / n})
        print("Universal fallback loaded:", len(result))
        return result if len(result) > 0 else None
    except Exception as e:
        print("Universal fallback error:", e)
        return None


def normalize_holdings(holdings):
    total = sum(h["weight"] for h in holdings)
    if total <= 0:
        return holdings
    return [{
        "ticker": h["ticker"],
        "weight": h["weight"] / total} for h in holdings]


async def get_etf_holdings(etf_ticker):
    ticker = etf_ticker.upper()
    holdings = await load_yahoo_full_holdings(ticker)
    if holdings:
        base = validate_and_normalize(holdings)
        if not base:
            holdings = None
        else:
            coverage = sum(h["weight"] for h in base)
            print(f"Yahoo holdings coverage: {coverage:.2%}")
            if coverage >= 0.80:
                print("Using pure Yahoo holdings")
                return base
            if coverage < 0.40:
                print("Coverage too low → proxy fallback")
                proxy = await get_index_proxy(ticker)
                return [
                    {"ticker": t,
                    "weight": 1 / len(proxy)}
                    for t in proxy]
            print("Using Yahoo + proxy hybrid")
            proxy = await get_index_proxy(ticker)
            existing = {h["ticker"] for h in base}
            extra = [
                t for t in proxy
                if t not in existing][:30]
            missing = max(0, 1 - coverage)
            weight_extra = min(0.30, missing)
            weight_base = 1 - weight_extra
            base_part = [
                {"ticker": h["ticker"],
                "weight": h["weight"] * weight_base}for h in base]
            extra_part = [
                {"ticker": t,
                "weight": weight_extra / len(extra)}for t in extra]
            return normalize_holdings(base_part + extra_part)
    print("⚠️ Yahoo holdings fail → proxy fallback")
    proxy = await get_index_proxy(ticker)
    return [
        {"ticker": t, "weight": 1 / len(proxy)} for t in proxy]
