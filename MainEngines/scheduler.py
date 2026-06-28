from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from MainEngines.auto_invest_engine import run_auto_invest_for_user
from ProjectDataBase.models import PortfolioSettings, async_session
from sqlalchemy import select

scheduler = AsyncIOScheduler()
async def get_users_ready_for_auto_invest():
    async with async_session() as session:
        result = await session.scalars(
            select(PortfolioSettings).where(
                PortfolioSettings.auto_invest_enabled.is_(True),
                PortfolioSettings.next_auto_invest_at <= datetime.now(timezone.utc)))
        return result.all()

async def auto_invest_job():
    users = await get_users_ready_for_auto_invest()
    for user in users:
        try:
            await run_auto_invest_for_user(user.user_id, user.portfolio_id)
        except Exception as e:
            print("AUTO INVEST ERROR:", e)

def start_scheduler():
    scheduler.add_job(auto_invest_job,
        trigger="cron", hour=12, minute=0)
    scheduler.start()