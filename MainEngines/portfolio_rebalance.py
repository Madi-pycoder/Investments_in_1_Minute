MIN_WEIGHT_DRIFT = 0.015
MIN_TRADE_DOLLARS = 25


def calculate_rebalance(
    positions_data, target_weights, total_value,
    min_weight_drift=MIN_WEIGHT_DRIFT,
    min_trade_value=MIN_TRADE_DOLLARS):
    print(target_weights)
    print([
        (p["ticker"], p["weight"])
        for p in positions_data])
    trades = []
    skipped_small = 0
    low_diversification = len(positions_data) <= 3
    for pos in positions_data:
        ticker = pos["ticker"]
        current_value = pos["value"]
        current_weight = (current_value / total_value)
        target_weight = target_weights.get(ticker, current_weight)
        weight_diff = abs(current_weight - target_weight)
        force_rebalance = (current_weight > 0.4 or low_diversification)
        if weight_diff < min_weight_drift and not force_rebalance:
            skipped_small += 1
            continue
        target_value = (total_value * target_weight)
        diff = target_value - current_value
        if abs(diff) < min_trade_value:
            skipped_small += 1
            continue
        trades.append({
            "ticker": ticker,
            "action": (
                "Покупка"
                if diff > 0
                else "Продажа"), "amount": round(abs(diff), 2)})
    return {
        "trades": trades,
        "skipped_small": skipped_small}
