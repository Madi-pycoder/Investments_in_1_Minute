import asyncio
import logging_config
import logging
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from aiogram import Bot, Dispatcher
from config import TOKEN, REDIS_URL
from error_logging import ErrorLoggingMiddleware
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
from VisualFeatures.projectinfo import router as project_info_router
from VisualFeatures.analytics_admin import router as analytics_admin_router
from ReviewsAndReferrals.referral import router as referral_router
from MainEngines.scheduler import start_scheduler, set_bot


async def main():
    bot = Bot(token=TOKEN)
    set_bot(bot)
    redis = Redis.from_url(REDIS_URL)
    storage = RedisStorage(redis)
    dp = Dispatcher(storage=storage)
    start_scheduler()
    dp.update.middleware(ErrorLoggingMiddleware())
    dp.include_router(main_router)
    dp.include_router(market_router)
    dp.include_router(trading_router)
    dp.include_router(account_router)
    dp.include_router(portfolio_auto_router)
    dp.include_router(portfolio_view_router)
    dp.include_router(portfolio_sim_router)
    dp.include_router(portfolio_reb_router)
    dp.include_router(portfolio_brain_router)
    dp.include_router(project_info_router)
    dp.include_router(analytics_admin_router)
    dp.include_router(referral_router)
    print("🚀 Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.exception("Bot crashed")
        raise