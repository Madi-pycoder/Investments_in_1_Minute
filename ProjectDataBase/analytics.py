import asyncio
from datetime import datetime, timezone, timedelta
import time
from sqlalchemy import select, func
from ProjectDataBase.models import (
    async_session,
    AnalyticsEvent, DailyAnalyticsSnapshot,
    Owner, Portfolio,
    Goal, UserProfileDB)


class AnalyticsService:
    @staticmethod
    async def track_event(
        *, user_id: int, event_name: str, category: str | None = None,
        duration_ms: int | None = None, success: bool = True,
        event_data: dict | None = None,
        source_attribution: str | None = None,
        event_version: int = 1):
        async with async_session() as session:
            session.add(
                AnalyticsEvent(
                    user_id=user_id, event_name=event_name,
                    category=category, event_version=event_version,
                    source_attribution=source_attribution,
                    duration_ms=duration_ms, success=success,
                    event_data=event_data or {},
                    created_at=datetime.now(timezone.utc)))
            await session.commit()


    @staticmethod
    async def timed_event(
        user_id: int, event_name: str, coro,
        category: str | None = None,
        event_data: dict | None = None,
        source_attribution: str | None = None,):
        start = time.perf_counter()
        try:
            result = await coro
            duration_ms = int((time.perf_counter() - start) * 1000)
            asyncio.create_task(
            AnalyticsService.track_event(
                user_id=user_id, event_name=event_name, category=category,
                duration_ms=duration_ms,
                success=True,
                event_data=event_data,
                source_attribution=source_attribution,))
            return result
        except Exception as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            asyncio.create_task(AnalyticsService.track_event(
                user_id=user_id, event_name=event_name, category=category,
                duration_ms=duration_ms, success=False,
                event_data={
                    **(event_data or {}),
                    "error": str(e)}, source_attribution=source_attribution))
            raise

    @staticmethod
    async def measure(
        user_id: int, event_name: str, coro,
        category: str | None = None,
        event_data: dict | None = None,
        source_attribution: str | None = None,):
        return await AnalyticsService.timed_event(
            user_id=user_id,
            event_name=event_name,
            coro=coro,
            category=category,
            event_data=event_data,
            source_attribution=source_attribution)


    @staticmethod
    async def calculate_retention(days: int) -> float:
        today = datetime.now(timezone.utc).date()
        cohort_day = today - timedelta(days=days)
        async with async_session() as session:
            cohort_users_query = (
                select(Owner.tg_id).where(func.date(Owner.created_at) == cohort_day))
            cohort_users = (await session.execute(cohort_users_query)).scalars().all()
            if not cohort_users:
                return 0.0
            returned_users_query = (
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(AnalyticsEvent.user_id.in_(cohort_users),
                    func.date(AnalyticsEvent.created_at) == today))
            returned_users = await session.scalar(returned_users_query)
            return round((returned_users or 0) / len(cohort_users), 4)


    @staticmethod
    async def calculate_activation_rate() -> float:
        today = datetime.now(timezone.utc).date()
        async with async_session() as session:
            new_users = await session.scalar(
                select(func.count())
                .where(func.date(Owner.created_at) == today))
            activated_users = await session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(AnalyticsEvent.event_name.in_(
                        ["goal.created",
                            "analysis.completed",
                            "portfolio.created"]),
                    func.date(AnalyticsEvent.created_at) == today))
            if not new_users:
                return 0.0
            return round((activated_users or 0) / new_users, 4)


    @staticmethod
    async def calculate_rebalance_adoption() -> float:
        async with async_session() as session:
            total_users = await session.scalar(select(func.count(Owner.id)))
            rebalance_users = await session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(AnalyticsEvent.event_name
                    == "portfolio.rebalanced"))
            if not total_users:
                return 0.0
            return round((rebalance_users or 0) / total_users, 4)


    @staticmethod
    async def calculate_ai_engagement_rate() -> float:
        async with async_session() as session:
            total_users = await session.scalar(select(func.count(Owner.id)))
            ai_users = await session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(AnalyticsEvent.event_name.in_(
                        ["analysis.completed",
                        "ai.chat.used",
                        "ai.recommendation.used",])))
            if not total_users:
                return 0.0
            return round((ai_users or 0) / total_users, 4)


    @staticmethod
    async def calculate_auto_invest_conversion() -> float:
        async with async_session() as session:
            analyzed_users = await session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(AnalyticsEvent.event_name == "analysis.completed"))
            auto_invest_users = await session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(AnalyticsEvent.event_name == "auto_invest.enabled"))
            if not analyzed_users:
                return 0.0
            return round((auto_invest_users or 0) / analyzed_users, 4)


    @staticmethod
    async def calculate_avg_portfolio_size() -> float:
        async with async_session() as session:
            avg_size = await session.scalar(select(func.avg(Portfolio.cash)))
            return round(float(avg_size or 0), 2)


    @staticmethod
    async def calculate_avg_goals_per_user() -> float:
        async with async_session() as session:
            total_goals = await session.scalar(select(func.count(Goal.id)))
            total_users = await session.scalar(select(func.count(Owner.id)))
            if not total_users:
                return 0.0
            return round((total_goals or 0) / total_users, 2)


    @staticmethod
    async def calculate_churn_risk() -> float:
        threshold = (datetime.now(timezone.utc) - timedelta(days=7))
        async with async_session() as session:
            total_users = await session.scalar(select(func.count(Owner.id)))
            inactive_users = await session.scalar(select(func.count(UserProfileDB.user_id))
                .where(~UserProfileDB.user_id.in_(
                        select(AnalyticsEvent.user_id)
                        .where(AnalyticsEvent.created_at >= threshold))))
            if not total_users:
                return 0.0
            return round((inactive_users or 0) / total_users, 4)


    @staticmethod
    async def build_daily_snapshot():
        today = datetime.now(timezone.utc).date()
        async with async_session() as session:
            dau = await session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(func.date(AnalyticsEvent.created_at) == today))
            portfolio_opens = await session.scalar(select(func.count())
                .where(AnalyticsEvent.event_name == "portfolio.opened",
                    func.date(AnalyticsEvent.created_at) == today))
            auto_execs = await session.scalar(select(func.count())
                .where(AnalyticsEvent.event_name == "auto_invest.executed",
                    func.date(AnalyticsEvent.created_at) == today))
            avg_response = await session.scalar(select(func.avg(AnalyticsEvent.duration_ms))
                .where(AnalyticsEvent.duration_ms.is_not(None),
                    func.date(AnalyticsEvent.created_at) == today))
            snapshot = DailyAnalyticsSnapshot(
                date=today,
                dau=dau or 0,
                portfolio_opens=portfolio_opens or 0,
                auto_invest_execs=auto_execs or 0,
                avg_response_time=float(avg_response or 0),
                retention_d1=await AnalyticsService.calculate_retention(1),
                retention_d7=await AnalyticsService.calculate_retention(7),
                activation_rate=await AnalyticsService.calculate_activation_rate(),
                rebalance_adoption=await AnalyticsService.calculate_rebalance_adoption(),
                ai_engagement_rate=await AnalyticsService.calculate_ai_engagement_rate(),
                auto_invest_conversion=await AnalyticsService.calculate_auto_invest_conversion(),
                avg_portfolio_size=await AnalyticsService.calculate_avg_portfolio_size(),
                avg_goals_per_user=await AnalyticsService.calculate_avg_goals_per_user(),
                churn_risk_rate=await AnalyticsService.calculate_churn_risk())
            session.add(snapshot)
            await session.commit()

def build_portfolio_event_data(
        portfolio_id: int | None, positions, goals,
            metrics: dict | None = None,
            risk_profile: str | None = None,
            total_value: float = 0,
            cached_metrics: bool = False, profile=None,
            extra: dict | None = None,):
        positions = positions or []
        goals = goals or []
        metrics = metrics or {}
        sectors = metrics.get("sector_allocation") or {}
        top_sector = None
        top_sector_weight = 0
        if sectors:
            top_sector = max(sectors, key=sectors.get)
            top_sector_weight = sectors[top_sector]
        data = {
            "portfolio_id": portfolio_id,
            "portfolio_value": round(float(total_value or 0), 2),
            "positions_count": len(positions),
            "goals_count": len(goals),
            "risk_profile": risk_profile,
            "investment_style": getattr(profile, "investment_style", None),
            "has_shariah_goals": any(getattr(g, "compliance", None) == "shariah" for g in goals),
            "auto_invest_enabled": getattr(profile, "auto_invest_enabled", False),
            "market_regime": metrics.get("market_regime"),
            "volatility": metrics.get("volatility"),
            "diversification_score": metrics.get("diversification_score"),
            "expected_return": metrics.get("expected_return"),
            "top_sector": top_sector,
            "top_sector_weight": round(float(top_sector_weight or 0), 3),
            "cache_hit": bool(cached_metrics),
            "timestamp": datetime.now(timezone.utc).isoformat()}
        if extra: data.update(extra)
        return data