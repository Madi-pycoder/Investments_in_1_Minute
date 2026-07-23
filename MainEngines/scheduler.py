import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from MainEngines.auto_invest_engine import run_auto_invest_for_user
from ProjectDataBase.models import PortfolioSettings, async_session, UserProfileDB
from MainEngines.notifications import get_notification
from sqlalchemy import select, update

scheduler = AsyncIOScheduler()
logger = logging.getLogger("halal")
_bot: Bot | None = None

def set_bot(bot):
    global _bot
    _bot = bot


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
            logger.info("AUTO INVEST ERROR:", e)


async def get_all_users():
    async with async_session() as session:
        result = await session.scalars(
            select(UserProfileDB.user_id)
            .where(UserProfileDB.welcome_completed == True))
        return result.all()


async def notification_job():
    if _bot is None:
        return
    bot = _bot
    users = await get_all_users()
    for user in users:
        try:
            text = await get_notification(user)
            await bot.send_message(user, text)
            async with async_session() as session:
                await session.execute(
                    update(UserProfileDB)
                    .where(UserProfileDB.user_id == user)
                    .values(last_notification_sent_at=datetime.now(timezone.utc)))
                await session.commit()
        except Exception as e:
            logger.error("Notification error: %s", e)


def start_scheduler():
    scheduler.add_job(auto_invest_job,
        trigger="cron", hour=12, minute=0)
    scheduler.add_job(notification_job, trigger="cron",
        day_of_week="mon,thu", hour=18, minute=0)
    scheduler.start()