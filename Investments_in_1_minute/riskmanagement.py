import yfinance as yf
import numpy as np
import pandas as pd

history_cache = {}

def safe_history(ticker, period="1y"):
    key = f"{ticker}_{period}"

    if key in history_cache:
        return history_cache[key]

    try:
        hist = yf.download(ticker, period=period, progress=False, timeout=10, threads=False)

        if hist is None or not hasattr(hist, "empty") or hist.empty:
            return None

        history_cache[key] = hist
        return hist

    except Exception:
        return None


def ensure_series(data):
    if isinstance(data, pd.DataFrame):
        return data.iloc[:, 0]
    return data



# ---------------------------
# 1. VOLATILITY
# ---------------------------
async def calculate_volatility(ticker: str, period="1y"):
    hist = yf.download(ticker, period=period, progress=False, timeout=10, threads=False)

    if hist.empty:
        return None

    returns = ensure_series(hist["Close"].pct_change().dropna())


    if isinstance(returns, pd.DataFrame):
        returns = returns.iloc[:, 0]

    daily_vol = returns.std()

    annual_vol = daily_vol * np.sqrt(252)

    return round(float(annual_vol * 100), 2)


# ---------------------------
# 2. MAX DRAWDOWN
# ---------------------------
async def calculate_max_drawdown(ticker: str, period="5y"):
    hist = yf.download(ticker, period=period, progress=False, timeout=10, threads=False)

    if hist.empty:
        return None

    close = ensure_series(hist["Close"])


    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    cumulative = close / close.iloc[0]
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak

    max_dd = drawdown.min()

    return round(float(max_dd * 100), 2)


# ---------------------------
# 3. BETA vs S&P 500
# ---------------------------
async def calculate_beta(ticker: str, period="1y"):
    stock = yf.Ticker(ticker)
    market = yf.Ticker("^GSPC")  # S&P 500 index

    hist_stock = stock.history(period=period)
    hist_market = market.history(period=period)

    if hist_stock.empty or hist_market.empty:
        return None

    returns_stock = hist_stock["Close"].pct_change().dropna()
    returns_market = hist_market["Close"].pct_change().dropna()
    df = pd.concat([returns_stock, returns_market], axis=1).dropna()
    df.columns = ["stock", "market"]
    covariance = df.cov().iloc[0, 1]
    market_var = df["market"].var()
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



# ---------------------------
# ETF RISK
# ---------------------------

async def calculate_etf_risk(ticker: str):

    vol = await calculate_volatility(ticker)
    dd = await calculate_max_drawdown(ticker)
    beta = await calculate_beta(ticker)
    sharpe = await calculate_sharpe_ratio(ticker)

    risk_score = calculate_risk_score(vol, dd, beta, sharpe)
    risk_label = get_risk_label(risk_score)

    return {
        "volatility": vol,
        "drawdown": dd,
        "beta": beta,
        "sharpe": sharpe,
        "risk_score": risk_score,
        "risk_label": risk_label
    }



# ---------------------------
# 5. SHARPE RATIO
# ---------------------------
async def calculate_sharpe_ratio(ticker: str, period="1y", risk_free_rate=0.02):
    hist = yf.download(ticker, period=period, progress=False, timeout=10, threads=False)

    if hist.empty:
        return None

    returns = ensure_series(hist["Close"].pct_change().dropna())

    excess_returns = returns - (risk_free_rate / 252)

    sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()

    return round(float(sharpe), 2)



def get_risk_label(score):

    if score is None:
        return "Unknown"

    if score >= 80:
        return "LOW RISK 🟢"

    if score >= 60:
        return "MODERATE RISK 🟡"

    if score >= 40:
        return "HIGH RISK 🟠"

    return "VERY HIGH RISK 🔴"



# ---------------------------
# PORTFOLIO VOLATILITY
# ---------------------------
async def calculate_portfolio_volatility(positions):

    if not positions:
        return None

    prices = {}
    weights = []

    for pos in positions:
        ticker = pos["ticker"]
        weight = pos["weight"]

        hist = safe_history(ticker, "1y")

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
        if pos["ticker"] in valid_tickers
    ])

    weights = weights / np.sum(weights)

    cov_matrix = df.cov() * 252

    portfolio_vol = np.sqrt(
        np.dot(weights.T, np.dot(cov_matrix, weights))
    )

    return round(float(portfolio_vol * 100), 2)






# ---------------------------
# DIVERSIFICATION SCORE
# ---------------------------
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
        return "EXTREME 🔴"

    if max_weight > 0.35:
        return "HIGH 🟠"

    if max_weight > 0.2:
        return "MODERATE 🟡"

    return "GOOD 🟢"




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
        "risk_score": risk_score
    }



def calculate_portfolio_risk_score(volatility, diversification):

    if volatility is None or diversification is None:
        return None

    score = 100

    # volatility penalty
    if volatility > 35:
        score -= 30
    elif volatility > 25:
        score -= 20
    elif volatility > 15:
        score -= 10

    # diversification bonus
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
        alerts.append("⚠️ Portfolio volatility is very high")

    if risk.get("diversification", 0) < 40:
        alerts.append("⚠️ Portfolio poorly diversified")

    if risk["concentration"] in ["HIGH 🟠", "EXTREME 🔴"]:
        alerts.append("⚠️ Portfolio concentration risk")

    return alerts



async def calculate_optimal_weights(positions):

    tickers = [p["ticker"] for p in positions]

    returns = {}

    for ticker in tickers:
        hist = safe_history(ticker, "1y")
        if hist is None:
            continue

        if hist.empty:
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

    num_assets = len(mean_returns)

    best_vol = 999
    best_weights = None

    for _ in range(500):

        weights = np.random.random(num_assets)
        weights /= np.sum(weights)

        vol = np.sqrt(
            np.dot(weights.T, np.dot(cov_matrix * 252, weights))
        )

        if vol < best_vol:
            best_vol = vol
            best_weights = weights

    portfolio_var = np.dot(


        weights.T, np.dot(cov_matrix, weights))

    optimal = {}

    for i, ticker in enumerate(mean_returns.index):
        optimal[ticker] = round(float(weights[i]), 3)

    return optimal



async def calculate_efficient_frontier(positions, simulations=500):

    tickers = [p["ticker"] for p in positions]

    returns = {}

    for ticker in tickers:
        hist = safe_history(ticker, "1y")
        if hist is None:
            continue

        if hist.empty:
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
            np.dot(weights.T, np.dot(cov_matrix * 252, weights))
        )

        risk_free_rate = 0.02

        sharpe = (portfolio_return - risk_free_rate) / portfolio_vol \
            if portfolio_vol else 0

        results.append({
            "return": float(portfolio_return),
            "volatility": float(portfolio_vol),
            "sharpe": float(sharpe)
        })

    return results



# ---------------------------
# MONTE CARLO PORTFOLIO SIMULATION
# ---------------------------
async def monte_carlo_portfolio(positions, simulations=300, days=126):

    if not positions or len(positions) < 2:
        return None

    tickers = [p["ticker"] for p in positions]

    returns = {}

    for ticker in tickers:

        hist = safe_history(ticker, "1y")
        if hist is None:
            continue

        if hist.empty:
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
        if p["ticker"] in valid_tickers
    ])

    weights = weights / np.sum(weights)

    mean_returns = df.mean()
    cov_matrix = df.cov()


    chol = np.linalg.cholesky(cov_matrix)

    portfolio_results = []

    for _ in range(simulations):

        rand = np.random.normal(size=(days, len(mean_returns)))

        correlated = rand @ chol

        daily_returns = correlated + mean_returns.values

        portfolio_daily = daily_returns @ weights

        portfolio_path = np.cumprod(1 + portfolio_daily)

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
        "cvar": round(float(cvar * 100), 2)
    }



# ---------------------------
# STRESS TESTING
# ---------------------------

def stress_test_portfolio(positions):

    if not positions:
        return None

    scenarios = {
        "2008 Crisis": -0.50,
        "Dotcom Crash": -0.45,
        "COVID Crash": -0.35,
        "Inflation Shock": -0.25,
        "Mild Correction": -0.10
    }

    results = {}

    for name, shock in scenarios.items():

        portfolio_loss = 0

        for pos in positions:

            weight = pos["weight"]

            loss = weight * shock

            portfolio_loss += loss

        results[name] = round(portfolio_loss * 100, 2)

    return results
