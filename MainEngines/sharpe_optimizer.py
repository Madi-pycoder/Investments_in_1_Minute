from ProjectDataBase.market_data_service import get_price_history
import pandas as pd

async def optimize_by_sharpe(tickers):
    returns = {}
    risks = {}
    for t in tickers:
        hist = await get_price_history(t)
        closes = [
            h.close
            for h in hist
            if h.close is not None]
        if len(closes) < 30:
            continue
        series = pd.Series(closes)
        daily_returns = (series.pct_change().dropna())
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
    sharpe_scores = {
        t: returns[t] / risks[t]
        for t in returns}
    total = sum(abs(v) for v in sharpe_scores.values())
    return {
        t: abs(s) / total if total else 0
        for t, s in sharpe_scores.items()}