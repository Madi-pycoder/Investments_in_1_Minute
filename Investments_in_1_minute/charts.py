# ---------------------------
# PORTFOLIO GROWTH GRAPH
# ---------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd

def generate_portfolio_growth_graph(positions):

    if not positions:
        return None

    tickers = [p["ticker"] for p in positions]
    weights = {p["ticker"]: p["weight"] for p in positions}

    try:
        data = yf.download(
            tickers=tickers,
            period="1y",
            group_by="ticker",
            threads=True
        )
    except Exception:
        return None

    returns_data = {}

    for ticker in tickers:
        try:
            hist = data[ticker]["Close"]
            returns = hist.pct_change().dropna()
            returns_data[ticker] = returns * weights[ticker]
        except Exception:
            continue

    if not returns_data:
        return None

    df = pd.DataFrame(returns_data).dropna()

    portfolio_returns = df.sum(axis=1)
    cumulative = (1 + portfolio_returns).cumprod()

    plt.figure(figsize=(8,6))
    plt.plot(cumulative)

    plt.title("Portfolio Growth (1Y)")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value")

    path = "portfolio_growth.png"

    plt.savefig(path, bbox_inches="tight")
    plt.close()

    return path




# ---------------------------
# STOCK / ETF PRICE GRAPH
# ---------------------------

def generate_asset_growth_graph(ticker):

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist is None or hist.empty:
            return None

    except Exception:
        return None

    plt.figure(figsize=(8,6))

    plt.plot(hist["Close"])

    plt.title(f"{ticker} Price (1Y)")
    plt.xlabel("Time")
    plt.ylabel("Price")

    path = f"{ticker}_price.png"

    plt.savefig(path, bbox_inches="tight")
    plt.close()

    return path



# ---------------------------
# PORTFOLIO SECTOR ALLOCATION
# ---------------------------

def generate_sector_allocation_chart(sectors):

    if not sectors:
        return None

    labels = list(sectors.keys())
    values = list(sectors.values())

    plt.figure(figsize=(7,7))

    plt.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90
    )

    plt.title("Portfolio Sector Allocation")

    path = "portfolio_sectors.png"

    plt.savefig(path, bbox_inches="tight")
    plt.close()

    return path