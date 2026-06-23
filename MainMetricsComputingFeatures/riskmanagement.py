import asyncio
import time
import numpy as np
import pandas as pd
from ProjectDataBase.cache import (hist_cache, RETURNS_CACHE, get_cached, set_cached,
    PORTFOLIO_VOL_CACHE, RISK_METRICS_CACHE, RISK_METRICS_TTL)
from ProjectDataBase.market_data_service import calculate_volatility_cached, calculate_drawdown_cached
from sqlalchemy import select
from ProjectDataBase.models import HistoricalPrice, async_session
from scipy.optimize import minimize
TURNOVER_PENALTY = 0.15
MAX_WEIGHT = 0.40
MIN_WEIGHT = 0.02
async def get_history_df(ticker: str, days: int = 365):
    cache_key = f"{ticker}_{days}"
    cached = hist_cache.get(cache_key)
    if cached:
        ts, value = cached
        if time.time() - ts < 600:
            return value
    async with async_session() as session:
        result = await session.scalars(
            select(HistoricalPrice).where(HistoricalPrice.ticker == ticker).order_by(HistoricalPrice.date))
        rows = result.all()
    if not rows:
        return None
    data = {
        "Close": [r.close for r in rows if r.close is not None]}
    if len(data["Close"]) < 2:
        return None
    df = pd.DataFrame(data)
    hist_cache[cache_key] = (time.time(), df)
    return df

def ensure_series(data):
    if isinstance(data, pd.DataFrame):
        return data.iloc[:, 0]
    return data

async def build_returns_dataframe(positions):
    cache_key = tuple(sorted(p["ticker"] for p in positions))
    cached = RETURNS_CACHE.get(cache_key)
    if cached:
        ts, value = cached
        if time.time() - ts < 900:
            return value
    returns = {}
    tasks = [
        get_history_df(p["ticker"])
        for p in positions]
    histories = await asyncio.gather(*tasks)
    for pos, hist in zip(positions, histories):
        if hist is None or hist.empty:
            continue
        r = hist["Close"].pct_change().dropna()
        if len(r) < 30:
            continue
        returns[pos["ticker"]] = r
    if not returns:
        return None
    df = pd.DataFrame(returns).dropna()
    if df.empty:
        return None
    RETURNS_CACHE[cache_key] = (time.time(), df)
    return df

def make_portfolio_cache_key(positions):
    normalized = sorted(
        [(p["ticker"], round(p["weight"], 4))for p in positions])
    return tuple(normalized)

async def calculate_volatility(ticker: str, period="1y"):
    hist = await get_history_df(ticker)
    if hist is None or hist.empty:
        return None
    returns = ensure_series(hist["Close"].pct_change().dropna())
    if len(returns) < 2:
        return None
    daily_vol = returns.std()
    annual_vol = daily_vol * np.sqrt(252)
    return round(float(annual_vol * 100), 2)

async def calculate_max_drawdown(ticker: str):
    hist = await get_history_df(ticker)
    if hist is None or hist.empty:
        return None
    close = hist["Close"]
    cumulative = close / close.iloc[0]
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    max_dd = drawdown.min()
    return round(float(max_dd * 100), 2)

async def calculate_beta(ticker: str):
    hist_stock = await get_history_df(ticker)
    hist_market = await get_history_df("SPY")
    if hist_stock is None or hist_market is None:
        return None
    returns_stock = hist_stock["Close"].pct_change().dropna()
    returns_market = hist_market["Close"].pct_change().dropna()
    df = pd.concat([returns_stock, returns_market], axis=1).dropna()
    if len(df) < 2:
        return None
    df.columns = ["stock", "market"]
    covariance = df.cov().iloc[0, 1]
    market_var = df["market"].var()
    if market_var == 0:
        return None
    beta = covariance / market_var
    return round(float(beta), 2)

def calculate_risk_score(volatility, drawdown, beta, sharpe):
    if None in (volatility, drawdown, beta, sharpe):
        return None
    score = 100
    if volatility > 45:
        score -= 25
    elif volatility > 30:
        score -= 15
    elif volatility > 20:
        score -= 5
    if abs(drawdown) > 60:
        score -= 25
    elif abs(drawdown) > 40:
        score -= 15
    elif abs(drawdown) > 25:
        score -= 5
    if beta > 1.6:
        score -= 15
    elif beta > 1.3:
        score -= 10
    if sharpe > 2:
        score += 10
    elif sharpe > 1:
        score += 5
    elif sharpe < 0.5:
        score -= 10
    return max(min(score, 100), 0)

async def calculate_etf_risk(ticker: str):
    start = time.perf_counter()
    vol, dd, beta, sharpe = await asyncio.gather(
        calculate_volatility_cached(ticker),
        calculate_drawdown_cached(ticker),
        calculate_beta(ticker),
        calculate_sharpe_ratio(ticker))
    risk_score = calculate_risk_score(vol, dd, beta, sharpe)
    risk_label = get_risk_label(risk_score)
    print("ETF INFO-Risk:", time.perf_counter() - start)
    return {
        "volatility": vol,
        "drawdown": dd,
        "beta": beta,
        "sharpe": sharpe,
        "risk_score": risk_score,
        "risk_label": risk_label}

async def calculate_sharpe_ratio(ticker: str, risk_free_rate=0.02):
    hist = await get_history_df(ticker)
    if hist is None or hist.empty:
        return None
    returns = hist["Close"].pct_change().dropna()
    if len(returns) < 2:
        return None
    excess_returns = returns - (risk_free_rate / 252)
    std = excess_returns.std()
    if std == 0:
        return None
    sharpe = np.sqrt(252) * excess_returns.mean() / std
    return round(float(sharpe), 2)

def get_risk_label(score):
    if score is None:
        return "Unknown"
    if score >= 80:
        return "Низкий Риск 🟢"
    if score >= 60:
        return "Средний Риск 🟡"
    if score >= 40:
        return "Высокий Риск 🟠"
    return "Очень Высокий Риск 🔴"

async def calculate_portfolio_volatility(positions):
    if not positions:
        return None
    cache_key = make_portfolio_cache_key(positions)
    cached = get_cached(PORTFOLIO_VOL_CACHE, cache_key, 300)
    if cached:
        ts, value = cached
        if time.time() - ts < 300:
            return value
    prices = {}
    weights = []
    for pos in positions:
        ticker = pos["ticker"]
        weight = pos["weight"]
        hist = await get_history_df(ticker)
        if hist is None or hist.empty:
            continue
        close = hist["Close"]
        close = ensure_series(close)
        returns = close.pct_change().dropna()
        if not isinstance(returns, pd.Series) or len(returns) < 2:
            continue
        prices[ticker] = returns
        weights.append(weight)
    if not prices or len(prices) < 2:
        return None
    df = pd.DataFrame(prices).dropna()
    valid_tickers = list(df.columns)
    weights = np.array([
        pos["weight"]
        for pos in positions
        if pos["ticker"] in valid_tickers])
    weights = weights / np.sum(weights)
    cov_matrix = df.cov() * 252
    portfolio_vol = np.sqrt(
        np.dot(weights.T, np.dot(cov_matrix, weights)))
    result = round(float(portfolio_vol * 100), 2)
    set_cached(PORTFOLIO_VOL_CACHE, cache_key, result)
    return result

def calculate_diversification_score(positions):
    if not positions:
        return None
    weights = [p["weight"] for p in positions]
    hhi = sum(w**2 for w in weights)
    score = (1 - hhi) * 100
    return round(score, 2)

def calculate_concentration_risk(positions):
    if not positions:
        return None
    max_weight = max(p["weight"] for p in positions)
    if max_weight > 0.5:
        return "Слишком Крупная Доля 🔴"
    if max_weight > 0.35:
        return "Большая Доля 🟠"
    if max_weight > 0.2:
        return "Умеренная Доля 🟡"
    return "Хорошая Диверсификация 🟢"

async def calculate_portfolio_risk(positions):
    if not positions:
        return None
    vol = await calculate_portfolio_volatility(positions)
    diversification = calculate_diversification_score(positions)
    concentration = calculate_concentration_risk(positions)
    risk_score = calculate_portfolio_risk_score(vol, diversification)
    return {
        "volatility": vol,
        "diversification": diversification,
        "concentration": concentration,
        "risk_score": risk_score}

def calculate_portfolio_risk_score(volatility, diversification):
    if volatility is None or diversification is None:
        return None
    score = 100
    if volatility > 35:
        score -= 30
    elif volatility > 25:
        score -= 20
    elif volatility > 15:
        score -= 10
    if diversification > 80:
        score += 5
    elif diversification < 40:
        score -= 15
    return max(min(score, 100), 0)

def generate_risk_alerts(risk):
    alerts = []
    if not risk:
        return alerts
    if risk["volatility"] and risk["volatility"] > 30:
        alerts.append("⚠️ Портфель сильно колеблется")
    if risk.get("diversification", 0) < 40:
        alerts.append("⚠️ Активы недостаточно диверсифицированы")
    if risk["concentration"] in ["Большая Доля 🟠", "Слишком Крупная Доля 🔴"]:
        alerts.append("⚠️ Слишком большая доля вложена в один актив")
    return alerts

async def calculate_optimal_weights(positions, turnover_penalty=TURNOVER_PENALTY):
    if not positions:
        return None
    df = await build_returns_dataframe(positions)
    if df is None or df.empty:
        return None
    tickers = list(df.columns)
    cov_matrix = df.cov() * 252
    current_weights = np.array([
        p["weight"]
        for p in positions
        if p["ticker"] in tickers])
    current_weights = current_weights / np.sum(current_weights)
    num_assets = len(current_weights)
    def objective(weights):
        portfolio_vol = np.sqrt(
            np.dot(weights.T, np.dot(cov_matrix, weights)))
        turnover = np.sum(np.abs(weights - current_weights))
        return portfolio_vol + (turnover_penalty * turnover)
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [
        (MIN_WEIGHT, MAX_WEIGHT)
        for _ in range(num_assets)]
    result = minimize(
        objective,
        current_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 100, "disp": False})
    if not result.success:
        return {
            p["ticker"]: p["weight"]
            for p in positions}
    optimal = {}
    for i, ticker in enumerate(tickers):
        optimal[ticker] = round(float(result.x[i]), 4)
    return optimal


async def calculate_efficient_frontier(positions, simulations=500):
    tickers = [p["ticker"] for p in positions]
    returns = {}
    for ticker in tickers:
        hist = await get_history_df(ticker)
        if hist is None:
            continue
        if hist is None or hist.empty:
            continue
        r = hist["Close"].pct_change().dropna()
        if isinstance(r, pd.DataFrame):
            r = r.iloc[:, 0]
        returns[ticker] = r
    if not returns:
        return None
    df = pd.DataFrame(returns).dropna()
    if df.empty:
        return None
    mean_returns = df.mean()
    cov_matrix = df.cov()
    results = []
    for _ in range(simulations):
        weights = np.random.random(len(mean_returns))
        weights /= np.sum(weights)
        portfolio_return = np.sum(mean_returns * weights) * 252
        portfolio_vol = np.sqrt(
            np.dot(weights.T, np.dot(cov_matrix * 252, weights)))
        risk_free_rate = 0.02
        sharpe = (portfolio_return - risk_free_rate) / portfolio_vol \
            if portfolio_vol else 0
        results.append({
            "return": float(portfolio_return),
            "volatility": float(portfolio_vol),
            "sharpe": float(sharpe)})
    return results

async def monte_carlo_portfolio(positions, simulations=300, days=126):
    if not positions or len(positions) < 2:
        return None
    tickers = [p["ticker"] for p in positions]
    returns = {}
    for ticker in tickers:
        hist = await get_history_df(ticker)
        if hist is None:
            continue
        if hist is None or hist.empty:
            continue
        r = hist["Close"].pct_change().dropna()
        if isinstance(r, pd.DataFrame):
            r = r.iloc[:, 0]
        returns[ticker] = r
    if not returns:
        return None
    if not returns:
        return None
    df = pd.DataFrame(returns).dropna()
    if df.empty:
        return None
    valid_tickers = list(df.columns)
    weights = np.array([
        p["weight"]
        for p in positions
        if p["ticker"] in valid_tickers])
    weights = weights / np.sum(weights)
    mean_returns = df.mean()
    cov_matrix = df.cov()
    cov_matrix += np.eye(len(cov_matrix)) * 1e-8
    portfolio_results = []
    for _ in range(simulations):
        rand = np.random.normal(size=(days, len(mean_returns)))
        try:
            L = np.linalg.cholesky(cov_matrix)
        except np.linalg.LinAlgError:
            cov_matrix += np.eye(len(cov_matrix)) * 1e-6
            L = np.linalg.cholesky(cov_matrix)
        correlated = rand @ L
        daily_returns = correlated + mean_returns.values
        portfolio_daily = daily_returns @ weights
        initial = 1.0
        portfolio_path = initial * np.cumprod(1 + portfolio_daily)
        portfolio_results.append(portfolio_path[-1])
    portfolio_results = np.array(portfolio_results)
    portfolio_returns = portfolio_results - 1
    mean_return = np.mean(portfolio_returns)
    worst_case = np.min(portfolio_returns)
    var_95 = np.percentile(portfolio_returns, 5)
    cvar = portfolio_returns[portfolio_returns <= var_95].mean()
    return {
        "expected_return": round(float(mean_return * 100), 2),
        "worst_case": round(float(worst_case * 100), 2),
        "var_95": round(float(var_95 * 100), 2),
        "cvar": round(float(cvar * 100), 2)}

def stress_test_portfolio(positions):
    if not positions:
        return None
    scenarios = {
        "Кризис 2008 года": -0.50,
        "Крах доткомов": -0.45,
        "Падние рынка во время COVID-19": -0.35,
        "Шокирующая инфляция": -0.25,
        "Небольшая коррекция рынка": -0.10}
    results = {}
    for name, shock in scenarios.items():
        portfolio_loss = 0
        for pos in positions:
            weight = pos["weight"]
            loss = weight * shock
            portfolio_loss += loss
        results[name] = round(portfolio_loss * 100, 2)
    return results


async def get_risk_metrics_cached(ticker):
    ticker = ticker.upper()
    cached = get_cached(RISK_METRICS_CACHE, ticker, RISK_METRICS_TTL)
    if cached:
        return cached
    vol = await calculate_volatility_cached(ticker)
    dd = await calculate_drawdown_cached(ticker)
    beta = await calculate_beta(ticker)
    sharpe = await calculate_sharpe_ratio(ticker)
    risk_score = calculate_risk_score(vol, dd, beta, sharpe)
    risk_label = get_risk_label(risk_score)
    result = {
        "volatility": vol,
        "drawdown": dd,
        "beta": beta,
        "sharpe": sharpe,
        "risk_score": risk_score,
        "risk_label": risk_label}
    set_cached(RISK_METRICS_CACHE, ticker, result)
    return result
