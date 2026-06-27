import numpy as np

def compute_trend(prices):
    if len(prices) < 200:
        return 0
    ma50 = np.mean(prices[-50:])
    ma200 = np.mean(prices[-200:])
    if ma50 > ma200:
        return 1
    elif ma50 < ma200:
        return -1
    return 0


def compute_momentum(prices):
    if len(prices) < 126:
        return 0
    ret_3m = prices[-1] / prices[-63] - 1
    ret_6m = prices[-1] / prices[-126] - 1
    score = 0
    if ret_3m > 0:
        score += 1
    else:
        score -= 1
    if ret_6m > 0:
        score += 1
    else:
        score -= 1
    return score / 2



def compute_volatility_regime(prices):
    returns = np.diff(prices) / prices[:-1]
    vol = np.std(returns) * np.sqrt(252)
    if vol < 0.15:
        return 1
    elif vol > 0.3:
        return -1
    return 0



def compute_drawdown(prices):
    peak = np.max(prices)
    current = prices[-1]
    dd = (current - peak) / peak
    if dd < -0.2:
        return -1
    elif dd > -0.05:
        return 1
    return 0



def compute_regime_score(prices):
    trend = compute_trend(prices)
    momentum = compute_momentum(prices)
    vol = compute_volatility_regime(prices)
    drawdown = compute_drawdown(prices)
    score = (trend * 2 + momentum * 1.5 + vol * 1.5 + drawdown * 2)
    return score