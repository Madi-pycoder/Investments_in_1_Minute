def calculate_rebalance(positions_data, target_weights, total_value):

    trades = []

    for pos in positions_data:

        ticker = pos["ticker"]
        current_value = pos["value"]

        target_weight = target_weights.get(ticker, 0)

        target_value = total_value * target_weight

        diff = target_value - current_value

        if abs(diff) < total_value * 0.01:
            continue

        action = "BUY" if diff > 0 else "SELL"

        trades.append({
            "ticker": ticker,
            "action": action,
            "amount": round(abs(diff), 2)
        })

    return trades



