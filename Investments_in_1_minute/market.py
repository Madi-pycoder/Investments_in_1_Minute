import yfinance as yf
import requests
import pandas as pd
from io import StringIO
from yahooquery import Ticker
import certifi
import ssl

ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

# ---------------------------
# INDEX PROXIES (fast fallback)
# ---------------------------

SP500_TOP = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
    "BRK-B", "LLY", "TSLA", "AVGO", "JPM", "UNH",
    "V", "XOM", "MA", "PG", "COST", "HD", "MRK",
    "ABBV", "ADBE", "CRM", "PEP", "KO", "AMD",
    "NFLX", "TMO", "LIN", "MCD", "INTC"
]

NASDAQ_PROXY = [
    "NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META",
    "AVGO", "WMT", "MU", "TMUS", "LRCX", "AMD", "NFLX",
    "CMCSA", "QCOM", "INTU"
]


async def get_index_proxy(ticker: str):

    ticker = ticker.upper()

    # 1. Direct mapping
    if ticker in ["SPY", "VOO", "IVV", "SPLG"]:
        return SP500_TOP

    if ticker in ["QQQ"]:
        return NASDAQ_PROXY

    # 2. Smart guess based on ETF type
    etf_type = await detect_etf_type(ticker)

    if etf_type == "vanguard":
        return SP500_TOP

    if etf_type == "invesco":
        return NASDAQ_PROXY

    # 3. Universal fallback (random diversified subset)
    universe = SP500_TOP + NASDAQ_PROXY
    return universe[:30]

# ---------------------------
# 1. STOCK INFO
# ---------------------------
async def get_stock_info(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="5y")
        if hist.empty:
            return {"error": "No market data"}

        def pct(period):
            try:
                return round(
                    (hist["Close"].iloc[-1] - hist["Close"].iloc[-period])
                    / hist["Close"].iloc[-period] * 100, 2)
            except:
                return None

        growth = {
            "1D": pct(1),
            "5D": pct(5),
            "1M": pct(22),
            "6M": pct(126),
            "1Y": pct(252),
            "5Y": pct(len(hist)-1)
        }

        ed = info.get("earningsDate")
        if isinstance(ed, list):
            ed = ed[0]
        dte = info.get("debtToEquity")
        bs = stock.balance_sheet

        try: receivables = bs.loc["Net Receivables"].iloc[0]
        except: receivables = None
        try: total_debt = bs.loc["Total Debt"].iloc[0]
        except: total_debt = info.get("totalDebt")
        try: total_cash = bs.loc["Cash And Cash Equivalents"].iloc[0]
        except: total_cash = info.get("totalCash")
        try: total_assets = bs.loc["Total Assets"].iloc[0]
        except: total_assets = info.get("totalAssets")

        return {
            "name": info.get("shortName"),
            "ticker": ticker.upper(),
            "debt_to_equity": dte/100 if dte else None,
            "pe": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "market_cap": info.get("marketCap"),
            "industry": info.get("industry"),
            "sector": info.get("sector"),
            "dividends": info.get("dividendRate"),
            "earnings_date": ed,
            "price": float(hist["Close"].iloc[-1]),
            "growth": growth,
            "receivables": receivables,
            "total_debt": total_debt,
            "total_cash": total_cash,
            "total_assets": total_assets,
            "revenue": info.get("totalRevenue"),
            "ebitda": info.get("ebitda"),
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# 2. ETF INFO
# ---------------------------
async def get_etf_info(ticker: str):
    try:
        etf = yf.Ticker(ticker)
        info = etf.info
        hist = etf.history(period="5y")
        if hist.empty:
            return {"error": "No market data"}

        def pct(period):
            try:
                return round(
                    (hist["Close"].iloc[-1] - hist["Close"].iloc[-period])
                    / hist["Close"].iloc[-period] * 100, 2)
            except:
                return None

        growth = {
            "1D": pct(1),
            "5D": pct(5),
            "1M": pct(22),
            "6M": pct(126),
            "1Y": pct(252),
            "5Y": pct(len(hist)-1)
        }

        return {
            "name": info.get("shortName"),
            "ticker": ticker.upper(),
            "nav": info.get("navPrice"),
            "net_assets": info.get("totalAssets"),
            "pe": info.get("trailingPE"),
            "expense": info.get("expenseRatio"),
            "price": float(hist["Close"].iloc[-1]),
            "growth": growth
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# 3. BATCH STOCKS
# ---------------------------
import asyncio

async def fetch_chunk(chunk, retries=3):

    for attempt in range(retries):
        try:
            t = Ticker(chunk, asynchronous=True)

            modules = t.get_modules(
                ["assetProfile", "financialData", "defaultKeyStatistics"]
            )

            result = {}

            for ticker in chunk:
                data = modules.get(ticker, {}) or {}

                profile = data.get("assetProfile", {})
                financial = data.get("financialData", {})
                stats = data.get("defaultKeyStatistics", {})

                result[ticker] = {
                    "industry": profile.get("industry"),
                    "sector": profile.get("sector"),
                    "market_cap": financial.get("marketCap") or stats.get("marketCap"),
                    "total_assets": financial.get("totalAssets"),
                    "total_debt": financial.get("totalDebt"),
                    "total_cash": financial.get("totalCash"),
                    "receivables": financial.get("totalReceivables"),
                }

            STOCKS_CACHE.update(result)

        except Exception as e:
            print(f"Retry {attempt+1} for chunk failed:", e)
            await asyncio.sleep(1.5 * (attempt + 1))

    print("Chunk полностью упал:", chunk)
    return {}


semaphore = asyncio.Semaphore(3)
STOCKS_CACHE = {}

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
                "receivables": None,
            }
            for t in tickers
        }

    final = {}

    for t in tickers:
        if t in result:
            final[t] = result[t]
        elif t in STOCKS_CACHE:
            final[t] = STOCKS_CACHE[t]["data"]
        else:
            # fallback proxy-level
            final[t] = {
                "industry": None,
                "sector": None,
                "market_cap": None,
                "total_assets": None,
                "total_debt": None,
                "total_cash": None,
                "receivables": None,
            }

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
        if h.get("ticker") and h.get("weight") is not None
    ]


# ---------------------------
# 4. ETF HOLDINGS LOADERS
# ---------------------------
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
                    "weight": float(weight)
                })

        print("Yahoo FULL loaded:", len(result))
        return result if len(result) > 0 else None

    except Exception as e:
        print("Yahoo FULL error:", e)
        return None





async def load_shariah_holdings(ticker):
    sources = [
        f"https://funds.wahedinvest.com/{ticker}/holdings.csv",
        f"https://www.sp-funds.com/wp-content/uploads/{ticker}-holdings.csv",
        f"https://cdn.sp-funds.com/{ticker}-holdings.csv",
    ]

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
                {
                    "ticker": str(row[ticker_col]).upper(),
                    "weight": float(row[weight_col]) / (100 if df[weight_col].max() > 1 else 1)
                }
                for _, row in df.iterrows()
                if row[ticker_col] and row[weight_col]
            ]

            if result:
                print("Shariah loaded:", len(result))
                return result

        except Exception as e:
            print(f"Shariah loader error ({url}):", e)
            continue

    return None



# ---------------------------
# INDEX LOADERS
# ---------------------------

SP500_URL = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
NASDAQ100_URL = "https://datahub.io/core/nasdaq-100/r/constituents.csv"


async def load_sp500_index():
    try:
        df = pd.read_csv(SP500_URL)
        tickers = df["Symbol"].tolist()

        weight = 1 / len(tickers)

        result = [
            {"ticker": t.upper(), "weight": weight}
            for t in tickers
        ]

        print("S&P 500 loaded:", len(result))
        return result

    except Exception as e:
        print("SP500 index error:", e)
        return None


NASDAQ100_URL = "https://datahub.io/core/nasdaq-100-companies/r/constituents.csv"

async def load_nasdaq100_index():
    try:
        df = pd.read_csv(NASDAQ100_URL)

        tickers = df["Symbol"].tolist()

        weight = 1 / len(tickers)

        result = [
            {"ticker": t.upper(), "weight": weight}
            for t in tickers
        ]

        print("NASDAQ 100 loaded:", len(result))
        return result

    except Exception as e:
        print("NASDAQ100 index error:", e)
        return None


# ---------------------------
# 5. FALLBACKS
# ---------------------------



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
                    "weight": 1 / n
                })

        print("Universal fallback loaded:", len(result))
        return result if len(result) > 0 else None

    except Exception as e:
        print("Universal fallback error:", e)
        return None


# ---------------------------
# 6. GET ETF HOLDINGS
# ---------------------------

INDEX_MAP = {
    "SPY": load_sp500_index,
    "VOO": load_sp500_index,
    "IVV": load_sp500_index,
    "SPLG": load_sp500_index,
}


async def get_etf_holdings(etf_ticker):

    ticker = etf_ticker.upper()

    if ticker in INDEX_MAP:
        holdings = await INDEX_MAP[ticker]()
        return validate_and_normalize(holdings)

    holdings = await load_yahoo_full_holdings(ticker)

    if holdings:
        print(f"Using Yahoo + proxy hybrid ({len(holdings)})")

        base = validate_and_normalize(holdings)

        proxy = await get_index_proxy(ticker)

        existing = {h["ticker"] for h in base}

        extra = [t for t in proxy if t not in existing]

        extra = extra[:30]

        if extra:
            weight_extra = 0.3
            weight_base = 0.7

            base = [
                {"ticker": h["ticker"], "weight": h["weight"] * weight_base}
                for h in base
            ]

            extra_part = [
                {"ticker": t, "weight": weight_extra / len(extra)}
                for t in extra
            ]

            return base + extra_part

        return base

    if not holdings:
        print("⚠️ Yahoo holdings fail → proxy fallback")

        proxy = await get_index_proxy(ticker)

        return [
            {"ticker": t, "weight": 1 / len(proxy)}
            for t in proxy
        ]


# ---------------------------
# 7. GET ETF HOLDINGS С SHARIAH-SCREENING
# ---------------------------
async def get_etf_holdings_shariah(etf_ticker, shariah_filter=None):

    holdings = await get_etf_holdings(etf_ticker)

    if holdings is None or len(holdings) == 0:
        print(f"No holdings for {etf_ticker}")
        return None


    if shariah_filter:
        filtered = [h for h in holdings if shariah_filter(h["ticker"])]
        if not filtered:
            print(f"Shariah filter removed all holdings for {etf_ticker}")
            return None


        total = sum(h["weight"] for h in filtered)
        holdings = [{"ticker": h["ticker"], "weight": h["weight"]/total} for h in filtered]

    print(f"Shariah holdings loaded for {etf_ticker}: {len(holdings)} tickers")
    return holdings
