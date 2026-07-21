import asyncio
import time
from ProjectDataBase.analytics import AnalyticsService
from ProjectDataBase.cache import portfolio_data_cache
from ProjectDataBase.data_provider import DataProvider
from ProjectDataBase import backend as rq
import logging

logger = logging.getLogger(__name__)


async def with_timeout(coro, timeout=5, default=None):
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except Exception as e:
        logger.info("ERROR:", e)
        return default

def get_portfolio_data_cached(portfolio_id):
    item = portfolio_data_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > 30:
        return None
    return item["data"]

async def load_portfolio_data(portfolio_id):
    cached = get_portfolio_data_cached(portfolio_id)
    if cached:
        return cached
    portfolio,positions, goals = await asyncio.gather(
        rq.get_portfolio(portfolio_id),
        rq.get_positions(portfolio_id),
        rq.get_goals(portfolio_id))
    positions = positions or []
    if not isinstance(positions, list):
        positions = []
    if not positions:
        return {
            "portfolio": portfolio,
            "positions": [],
            "positions_data": [],
            "stocks_batch": {},
            "prices_dict": {},
            "goals": []}
    tickers = [p.ticker for p in positions]
    provider = DataProvider()
    start = time.perf_counter()
    data = await provider.get_all(tickers)
    duration = int((time.perf_counter() - start) * 1000)
    prices_data = data["prices"]
    stocks_batch = data["stocks"]
    prices_dict = {
        t: float(d["price"])
        for t, d in zip(tickers, prices_data)
        if d and isinstance(d, dict) and "price" in d}
    asyncio.create_task(
    AnalyticsService.track_event(
        user_id=0,
        event_name="portfolio.load",
        category="performance",
        duration_ms=duration,
        event_data={
            "portfolio_id": portfolio_id,
            "positions": len(positions)}))
    result = {
        "portfolio": portfolio,
        "positions": positions,
        "stocks_batch": stocks_batch,
        "prices_dict": prices_dict,
        "goals": goals}
    portfolio_data_cache[portfolio_id] = {
        "ts": time.time(),
        "data": result}
    return result