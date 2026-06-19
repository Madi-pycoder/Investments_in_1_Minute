import numpy as np
from market_regime_factors import compute_regime_score

def normalize_prices(prices):
    if prices is None:
        return None
    if isinstance(prices, list):
        return np.array(prices)
    if isinstance(prices, (list, np.ndarray)):
        return np.array(prices)
    return None


def detect_market_regime(prices):
    prices = normalize_prices(prices)
    if prices is None or len(prices) < 200:
        return {"regime": "unknown", "score": 0}
    score = compute_regime_score(prices)
    if score >= 2:
        regime = "bull"
    elif score <= -2:
        regime = "crisis"
    elif score < 0:
        regime = "bear"
    else:
        regime = "sideways"
    return{
        "regime": regime,
        "score": score}


def classify_asset(ticker):
    safe = ["BND", "SUKUK", "TLT"]
    growth = ["QQQ", "TECH", "NVDA"]
    if ticker in safe:
        return "defensive"
    if ticker in growth:
        return "growth"
    return "neutral"


def apply_market_regime_shift(weights, regime):
    if not weights:
        return {}
    shifted = {}
    for ticker, w in weights.items():
        asset_type = classify_asset(ticker)
        if regime == "bull":
            if asset_type == "growth":
                w *= 1.2
            elif asset_type == "defensive":
                w *= 0.9
        elif regime == "bear":
            if asset_type == "growth":
                w *= 0.8
            elif asset_type == "defensive":
                w *= 1.1
        elif regime == "crisis":
            if asset_type == "growth":
                w *= 0.6
            elif asset_type == "defensive":
                w *= 1.3
        shifted[ticker] = w
    total = sum(shifted.values())
    return {k: v / total for k, v in shifted.items()} if total else weights