import yfinance as yf

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
                    (hist["Close"].iloc[-1] - hist["Close"].iloc[-period]) /
                    hist["Close"].iloc[-period] * 100, 2)
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

        return {
            "name": info.get("shortName"),
            "ticker": ticker.upper(),

            "debt_to_equity": info.get("debtToEquity"),
            "pe": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "market_cap": info.get("marketCap"),

            "dividends": info.get("dividendRate"),
            "earnings_date": ed,

            "price": float(hist["Close"].iloc[-1]),
            "growth": growth
        }

    except Exception as e:
        return {"error": str(e)}

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
                    (hist["Close"].iloc[-1] - hist["Close"].iloc[-period]) /
                    hist["Close"].iloc[-period] * 100, 2)
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