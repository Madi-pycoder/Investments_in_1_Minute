from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict
from sqlalchemy import select, update
from ProjectDataBase.models import (UserProfileDB,
                                    PortfolioSettings, async_session, Owner)


@dataclass
class UserProfile:
    user_id: int
    income: Optional[float] = None


@dataclass
class PortfolioProfile:
    portfolio_id: int
    monthly_budget: float = 0.0
    risk_tolerance: str = "medium"
    investment_style: str = "balanced"
    auto_invest_enabled: bool = False
    last_auto_invest: Optional[datetime] = None
    next_auto_invest_at: Optional[datetime] = None


async def create_user_profile(user_id: int):
    async with async_session() as session:
        owner = await session.scalar(
            select(Owner).where(Owner.tg_id == user_id))
        if not owner:
            owner = Owner(tg_id=user_id)
            session.add(owner)
            await session.flush()
        existing = await session.scalar(
            select(UserProfileDB)
            .where(UserProfileDB.user_id == user_id))
        if existing:
            return db_to_user_profile(existing)
        db_profile = UserProfileDB(user_id=user_id)
        session.add(db_profile)
        await session.commit()
        return db_to_user_profile(db_profile)


async def get_user_profile(user_id: int):
    async with async_session() as session:
        profile = await session.scalar(
            select(UserProfileDB)
            .where(UserProfileDB.user_id == user_id))
        if not profile:
            return None
        return db_to_user_profile(profile)


async def update_user_profile(user_id: int, **kwargs):
    async with async_session() as session:
        await session.execute(
            update(UserProfileDB)
            .where(UserProfileDB.user_id == user_id)
            .values(**kwargs))
        await session.commit()
        updated = await session.scalar(
            select(UserProfileDB)
            .where(UserProfileDB.user_id == user_id))
        return db_to_user_profile(updated)


def db_to_user_profile(db: UserProfileDB):
    return UserProfile(
        user_id=db.user_id,
        income=db.income)


async def create_portfolio_profile(portfolio_id: int):
    async with async_session() as session:
        existing = await session.scalar(
            select(PortfolioSettings)
            .where(PortfolioSettings.portfolio_id == portfolio_id))
        if existing:
            return db_to_portfolio_profile(existing)
        settings = PortfolioSettings(portfolio_id=portfolio_id)
        session.add(settings)
        await session.commit()
        return db_to_portfolio_profile(settings)


async def get_portfolio_profile(portfolio_id: int):
    async with async_session() as session:
        settings = await session.scalar(
            select(PortfolioSettings)
            .where(PortfolioSettings.portfolio_id == portfolio_id))
        if not settings:
            return None
        return db_to_portfolio_profile(settings)


async def update_portfolio_profile(portfolio_id: int, **kwargs):
    async with async_session() as session:
        await session.execute(
            update(PortfolioSettings)
            .where(PortfolioSettings.portfolio_id == portfolio_id)
            .values(**kwargs))
        await session.commit()
        updated = await session.scalar(
            select(PortfolioSettings)
            .where(PortfolioSettings.portfolio_id == portfolio_id))
        return db_to_portfolio_profile(updated)


def db_to_portfolio_profile(db: PortfolioSettings):
    return PortfolioProfile(
        portfolio_id=db.portfolio_id,
        monthly_budget=db.monthly_budget,
        risk_tolerance=db.risk_tolerance,
        investment_style=db.investment_style,
        auto_invest_enabled=db.auto_invest_enabled,
        last_auto_invest=db.last_auto_invest,
        next_auto_invest_at=db.next_auto_invest_at)


def get_effective_monthly_budget(portfolio_profile, total_value=None):
    if (portfolio_profile
        and portfolio_profile.monthly_budget > 0):
        return portfolio_profile.monthly_budget
    if total_value:
        return round(total_value * 0.03, 2)
    return 0


def get_risk_multiplier(portfolio_profile):
    mapping = {
        "low": 0.8,
        "medium": 1.0,
        "high": 1.2}
    return mapping.get(portfolio_profile.risk_tolerance, 1.0)


def to_dict(profile) -> Dict:
    return asdict(profile)