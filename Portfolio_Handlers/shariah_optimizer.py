from ProjectDataBase.market_data_service import calculate_volatility_cached

async def optimize_shariah_portfolio(positions_data, stocks_batch):
    halal_positions = []
    for pos in positions_data:
        ticker = pos["ticker"]
        data = stocks_batch.get(ticker, {})
        debt = data.get("total_debt", 0)
        assets = data.get("total_assets", 1)
        debt_ratio = debt / assets if assets else 0
        if debt_ratio < 0.33:
            vol = await calculate_volatility_cached(ticker)
            if vol:
                halal_positions.append({
                    "ticker": ticker,
                    "volatility": vol})
    if not halal_positions:
        return None
    inverse_vols = []
    for p in halal_positions:
        inverse_vols.append(1 / p["volatility"])
    total_inverse = sum(inverse_vols)
    target_weights = {}
    for i, pos in enumerate(halal_positions):
        weight = inverse_vols[i] / total_inverse
        target_weights[pos["ticker"]] = round(weight, 3)
    return target_weights