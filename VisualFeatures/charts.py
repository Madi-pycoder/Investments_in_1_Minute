import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ProjectDataBase.market_data_service import get_price_history
from io import BytesIO
import pandas as pd
import os

def cleanup_file(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print("PNG cleanup error:", e)


async def generate_portfolio_growth_graph(positions):
    if not positions:
        return None
    returns_data = {}
    for p in positions:
        ticker = p["ticker"]
        weight = p["weight"]
        hist = await get_price_history(ticker)
        closes = [
            h.close
            for h in hist
            if h.close is not None]
        if len(closes) < 30:
            continue
        series = pd.Series(closes)
        returns = (series.pct_change().dropna())
        returns_data[ticker] = returns * weight
    if not returns_data:
        return None
    df = pd.DataFrame(returns_data).dropna()
    if df.empty:
        return None
    portfolio_returns = df.sum(axis=1)
    cumulative = (1 + portfolio_returns).cumprod()
    plt.figure(figsize=(8, 6))
    plt.plot(cumulative)
    plt.title("Portfolio Growth (1Y)")
    plt.xlabel("Time")
    plt.ylabel("Portfolio Value")
    path = "portfolio_growth.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path


async def generate_asset_growth_graph(ticker):
    hist = await get_price_history(ticker)
    if not hist:
        return None
    closes = [h.close for h in hist if h.close is not None]
    if len(closes) < 2:
        return None
    plt.figure(figsize=(8, 6))
    plt.plot(closes)
    plt.title(f"{ticker} Price (1Y)")
    plt.xlabel("Time")
    plt.ylabel("Price")
    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight")
    plt.close()
    buffer.seek(0)
    return buffer

def generate_sector_allocation_chart(sectors):
    if not sectors:
        return None
    if not sectors:
        return None
    if len(sectors) <= 1:
        return None
    labels = list(sectors.keys())
    values = list(sectors.values())
    plt.figure(figsize=(7,7))
    plt.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90)
    plt.title("Portfolio Sector Allocation")
    path = "portfolio_sectors.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path