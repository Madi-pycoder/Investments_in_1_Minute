import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN

from handlersfrommadi.mainstart import router as main_router
from handlersfrommadi.markethandler import router as market_router
from handlersfrommadi.portfolio import router as portfolio_router
from handlersfrommadi.trading import router as trading_router
from handlersfrommadi.account import router as account_router

from models import async_main


async def main():
    await async_main()
    bot = Bot(token = TOKEN)
    dp = Dispatcher()
    dp.include_router(main_router)
    dp.include_router(market_router)
    dp.include_router(portfolio_router)
    dp.include_router(trading_router)
    dp.include_router(account_router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
