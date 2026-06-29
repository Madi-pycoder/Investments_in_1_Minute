from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from MainEngines.auto_invest_engine import run_auto_invest_for_user
from ProjectDataBase.models import PortfolioSettings, async_session, UserProfileDB
from MainEngines.notifications import get_notification
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


async def get_all_users():
    async with async_session() as session:
        result = await session.scalars(
            select(UserProfileDB.user_id).distinct())
        users = result.all()
        return list(users)


async def notification_job(bot):
    users = await get_all_users()
    for user in users:
        try:
            await bot.send_message(user.tg_id, get_notification())
        except Exception:
            pass

def start_scheduler():
    scheduler.add_job(auto_invest_job,
        trigger="cron", hour=12, minute=0)
    scheduler.add_job(notification_job, trigger="cron",
        day_of_the_week="mon, thu", hour=18, minute=0)
    scheduler.start()