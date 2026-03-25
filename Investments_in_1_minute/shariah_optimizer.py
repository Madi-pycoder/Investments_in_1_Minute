def optimize_shariah_portfolio(positions_data, stocks_batch):

    halal_positions = []

    for pos in positions_data:

        ticker = pos["ticker"]
        data = stocks_batch.get(ticker, {})

        debt = data.get("total_debt", 0)
        assets = data.get("total_assets", 1)

        debt_ratio = debt / assets if assets else 0

        # простое правило: debt < 33%
        if debt_ratio < 0.33:
            halal_positions.append(pos)

    if not halal_positions:
        return None

    weight = 1 / len(halal_positions)

    target_weights = {}

    for pos in halal_positions:
        target_weights[pos["ticker"]] = weight

    return target_weights