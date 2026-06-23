import numpy as np
from MarketFeatures.market_regime_factors import compute_regime_score

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
        return {
            "regime": "Недостаточно данных",
            "score": 0}
    score = compute_regime_score(prices)
    if score >= 2:
        regime = "Рост рынка 📈"
    elif score <= -2:
        regime = "Кризис 🚨"
    elif score < 0:
        regime = "Снижение рынка 📉"
    else:
        regime = "Боковое движение ➖"
    return{
        "regime": regime,
        "score": score}


def classify_asset(ticker):
    safe = ["BND", "SUKUK", "TLT"]
    growth = ["QQQ", "TECH", "NVDA"]
    if ticker in safe:
        return "Защитный актив"
    if ticker in growth:
        return "Актив роста"
    return "нейтральный"


def apply_market_regime_shift(weights, regime):
    if not weights:
        return {}
    shifted = {}
    for ticker, w in weights.items():
        asset_type = classify_asset(ticker)
        if regime == "Рост рынка 📈":
            if asset_type == "Актив роста":
                w *= 1.2
            elif asset_type == "Защитный актив":
                w *= 0.9
        elif regime == "Снижение рынка 📉":
            if asset_type == "Актив роста":
                w *= 0.8
            elif asset_type == "Защитный актив":
                w *= 1.1
        elif regime == "Кризис 🚨":
            if asset_type == "Актив роста":
                w *= 0.6
            elif asset_type == "Защитный актив":
                w *= 1.3
        shifted[ticker] = w
    total = sum(shifted.values())
    return {k: v / total for k, v in shifted.items()} if total else weights
