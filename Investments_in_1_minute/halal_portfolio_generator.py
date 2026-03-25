import yfinance as yf

async def generate_halal_portfolio(tickers, stocks_batch):

    halal = []

    for t in tickers:
        data = stocks_batch.get(t, {})

        debt = data.get("total_debt") or 0
        assets = data.get("total_assets") or 0

        if not assets:
            continue

        if debt / assets < 0.33:
            halal.append(t)

    if not halal:
        return None

    returns = {}

    for t in halal:
        hist = yf.Ticker(t).history(period="6mo")

        if hist.empty:
            continue

        r = hist["Close"].pct_change().dropna().mean()
        returns[t] = r

    if not returns:
        return None


    total = sum(abs(v) for v in returns.values())

    weights = {}

    for t, r in returns.items():
        weights[t] = abs(r) / total if total else 0

    return weights