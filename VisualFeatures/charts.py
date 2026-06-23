import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ProjectDataBase.market_data_service import get_price_history
from io import BytesIO
import os

def cleanup_file(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print("PNG cleanup error:", e)


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
