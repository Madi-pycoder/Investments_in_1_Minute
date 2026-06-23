import asyncio
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from aiogram import Bot, Dispatcher
from config import TOKEN, REDIS_URL
from VisualFeatures.mainstart import router as main_router
from VisualFeatures.markethandler import router as market_router
from MainEngines.trading import router as trading_router
from ProfileData.account import router as account_router
from Portfolio_Handlers.portfolio_auto_handler import (
    router as portfolio_auto_router)
from Portfolio_Handlers.portfolio_view_handler import (
    router as portfolio_view_router)
from Portfolio_Handlers.portfolio_simulation_handler import (
    router as portfolio_sim_router)
from Portfolio_Handlers.portfolio_rebalance_handler import (
    router as portfolio_reb_router)
from Portfolio_Handlers.portfolio_brain_handler import (
    router as portfolio_brain_router)
from scheduler import start_scheduler


async def main():
    bot = Bot(token=TOKEN)
    redis = Redis.from_url(REDIS_URL)
    storage = RedisStorage(redis)
    dp = Dispatcher(storage=storage)
    start_scheduler()
    dp.include_router(main_router)
    dp.include_router(market_router)
    dp.include_router(trading_router)
    dp.include_router(account_router)
    dp.include_router(portfolio_auto_router)
    dp.include_router(portfolio_view_router)
    dp.include_router(portfolio_sim_router)
    dp.include_router(portfolio_reb_router)
    dp.include_router(portfolio_brain_router)
    print("🚀 Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())