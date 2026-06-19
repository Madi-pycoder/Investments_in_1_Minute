import asyncio
from ProjectDataBase.market_data_service import get_cached_price, get_cached_fundamentals

class DataProvider:
    async def get_prices(self, tickers):
        tasks = [
            get_cached_price(t)
            for t in tickers]
        prices = await asyncio.gather(*tasks)
        return dict(zip(tickers, prices))

    async def get_stocks(self, tickers):
        tasks = [
            get_cached_fundamentals(t)
            for t in tickers]
        results = await asyncio.gather(*tasks)
        data = {}
        for f in results:
            if not f:
                continue
            data[f.ticker] = {
                "sector": f.sector,
                "industry": f.industry,
                "market_cap": f.market_cap,
                "quoteType": f.quote_type,}
        return data

    async def get_all(self, tickers):
        prices_task = asyncio.create_task(self.get_prices(tickers))
        stocks_task = asyncio.create_task(self.get_stocks(tickers))
        prices, stocks = await asyncio.gather(prices_task, stocks_task)
        return {
            "prices": prices,
            "stocks": stocks}