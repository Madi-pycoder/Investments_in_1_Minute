import asyncio
from market import get_stock_info, get_stocks_batch
import requets as rq
from requets import get_goals


async def load_portfolio_data(portfolio_id):
    portfolio = await rq.get_portfolio(portfolio_id)
    positions = await rq.get_positions(portfolio_id)

    if not positions:
        return {
            "portfolio": portfolio,
            "positions": [],
            "positions_data": []
        }

    tickers = [p.ticker for p in positions]

    stocks_batch_task = asyncio.create_task(get_stocks_batch(tickers))
    prices_task = asyncio.gather(*[get_stock_info(t) for t in tickers])
    goals_task = asyncio.create_task(get_goals(portfolio_id))

    stocks_batch, prices_data, goals = await asyncio.gather(
        stocks_batch_task,
        prices_task,
        goals_task
    )

    prices_dict = {
        t: float(d["price"])
        for t, d in zip(tickers, prices_data)
        if d and "price" in d
    }

    return {
        "portfolio": portfolio,
        "positions": positions,
        "stocks_batch": stocks_batch,
        "prices_dict": prices_dict,
        "goals": goals
    }
