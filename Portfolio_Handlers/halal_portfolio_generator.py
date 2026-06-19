from ProjectDataBase.market_data_service import get_price_history
import pandas as pd

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
        hist = await get_price_history(t)
        closes = [
            h.close
            for h in hist
            if h.close is not None]
        if len(closes) < 30:
            continue
        series = pd.Series(closes)
        r = (series.pct_change().dropna().mean())
        returns[t] = r
    if not returns:
        return None
    total = sum(abs(v) for v in returns.values())
    return {
        t: abs(r) / total if total else 0
        for t, r in returns.items()}