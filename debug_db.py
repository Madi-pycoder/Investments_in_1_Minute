from sqlalchemy import text
from ProjectDataBase.models import async_session
import asyncio

async def main():
    async with async_session() as session:
        r = await session.execute(
            text("SELECT COUNT(*) FROM historical_prices")
        )
        print(r.scalar())

asyncio.run(main())