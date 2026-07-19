from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, and_
from aiogram.types import Message
from ProjectDataBase.models import async_session, AnalyticsEvent, UserProfileDB
from GrowthSystem.service import GrowthService


class GrowthTriggers:
    @staticmethod
    async def check_first_analysis(user_id: int) -> bool:
        async with async_session() as session:
            count = await session.scalar(
                select(func.count())
                .where(and_(AnalyticsEvent.user_id == user_id,
                        AnalyticsEvent.event_name == "analysis.completed")))
            return count == 1

    @staticmethod
    async def check_third_analysis(user_id: int) -> bool:
        async with async_session() as session:
            count = await session.scalar(
                select(func.count())
                .where(and_(AnalyticsEvent.user_id == user_id,
                        AnalyticsEvent.event_name == "analysis.completed")))
            return count == 3

    @staticmethod
    async def check_first_deep_audit(user_id: int) -> bool:
        async with async_session() as session:
            count = await session.scalar(
                select(func.count())
                .where(and_(AnalyticsEvent.user_id == user_id,
                        AnalyticsEvent.event_name == "deep_audit.completed")))
            return count == 1

    @staticmethod
    async def check_week_activity(user_id: int) -> bool:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        async with async_session() as session:
            count = await session.scalar(
                select(func.count())
                .where(and_(AnalyticsEvent.user_id == user_id,
                        AnalyticsEvent.created_at >= week_ago)))
            return count >= 5

    @staticmethod
    async def check_onboarding_completed(user_id: int) -> bool:
        async with async_session() as session:
            profile = await session.scalar(
                select(UserProfileDB).where(UserProfileDB.user_id == user_id))
            return profile is not None and profile.welcome_completed

    @staticmethod
    async def trigger_after_first_analysis(message: Message) -> None:
        if await GrowthTriggers.check_first_analysis(message.from_user.id):
            await GrowthService.try_show_promo(
                message=message,
                promo_type="channel_invite",
                trigger="first_analysis")

    @staticmethod
    async def trigger_after_third_analysis(message: Message) -> None:
        if await GrowthTriggers.check_third_analysis(message.from_user.id):
            await GrowthService.try_show_promo(
                message=message,
                promo_type="channel_invite",
                trigger="third_analysis")

    @staticmethod
    async def trigger_after_deep_audit(message: Message) -> None:
        if await GrowthTriggers.check_first_deep_audit(message.from_user.id):
            await GrowthService.try_show_promo(
                message=message,
                promo_type="channel_invite",
                trigger="deep_audit")

    @staticmethod
    async def trigger_after_week_activity(message: Message) -> None:
        if await GrowthTriggers.check_week_activity(message.from_user.id):
            await GrowthService.try_show_promo(
                message=message,
                promo_type="channel_invite",
                trigger="week_activity")

    @staticmethod
    async def trigger_after_onboarding(message: Message) -> None:
        if await GrowthTriggers.check_onboarding_completed(message.from_user.id):
            await GrowthService.try_show_promo(
                message=message,
                promo_type="channel_invite",
                trigger="onboarding")