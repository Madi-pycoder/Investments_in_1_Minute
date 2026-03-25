import yfinance as yf


async def optimize_by_sharpe(tickers):

    returns = {}
    risks = {}

    for t in tickers:

        hist = yf.Ticker(t).history(period="6mo")

        if hist.empty:
            continue

        daily_returns = hist["Close"].pct_change().dropna()

        if len(daily_returns) < 10:
            continue

        mean_return = daily_returns.mean()
        volatility = daily_returns.std()

        if volatility == 0:
            continue

        returns[t] = mean_return
        risks[t] = volatility

    if not returns:
        return None

    sharpe_scores = {}

    for t in returns:
        sharpe_scores[t] = returns[t] / risks[t]

    total = sum(abs(v) for v in sharpe_scores.values())

    weights = {}

    for t, s in sharpe_scores.items():
        weights[t] = abs(s) / total if total else 0

    return weights