from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy import select
from ProjectDataBase.models import (async_session, UserProfileDB, Portfolio,
    Goal, PortfolioSettings, AnalyticsEvent, Position)
import random

NEW = [
"👋 Добро пожаловать! Попробуйте создать первую цель.",
"🚀 Начните путь к инвестициям с небольшой цели.",
"📈 Первый анализ занимает меньше минуты."]
GOALS = [
"🎯 Добавьте финансовую цель — рекомендации станут точнее.",
"💰 Даже небольшая цель помогает собрать лучший портфель.",
"📊 Цель — это основа инвестиционного плана."]
PORTFOLIO = [
"📦 Самое время собрать первый портфель.",
"🧩 Добавьте первый актив и получите рекомендации.",
"📈 Портфель откроет функции ребалансировки."]
REBALANCE = [
"⚖️ Проверьте, не пора ли ребалансировать портфель.",
"📊 Доли активов могли измениться.",
"🛡 Ребалансировка помогает удерживать риск."]
AUTO = [
"🤖 Автоинвест может экономить ваше время.",
"💵 Попробуйте автоматические покупки.",
"📈 Пусть портфель растёт регулярно."]
INACTIVE = [
"👋 Давно не виделись.",
"📊 За это время рынок изменился.",
"🚀 Посмотрите новые возможности."]
GROWTH = [
"🚀 Возможно появились новые компании роста.",
"📈 Посмотрите свежие идеи для роста."]
SAFE = [
"🛡 Проверьте устойчивые ETF.",
"📦 Возможно пора снизить риск."]
BALANCED = [
"⚖️ Проверьте баланс портфеля.",
"📊 Иногда небольшая корректировка даёт большой эффект."]
TICKER = [
"📈 Хотите снова посмотреть {ticker}?",
"🔍 Последний раз вы анализировали {ticker}.",
"📊 Возможно показатели {ticker} уже изменились."]



@dataclass
class NotificationContext:
    user_id: int
    has_portfolio: bool
    positions_count: int
    has_goal: bool
    goals_count: int
    auto_invest: bool
    last_analysis_days: int | None
    last_rebalance_days: int | None
    last_open_days: int | None
    investment_style: str
    portfolio_value: float
    first_analysis_done: bool
    first_goal_done: bool
    first_rebalance_done: bool
    first_auto_done: int
    last_ticker_analyzed: str | None
    last_ticker: str | None
    last_notification_sent_at: datetime | None


async def build_context(user_id: int):
    async with async_session() as session:
        profile = await session.get(UserProfileDB, user_id)
        last_notification_sent_at = profile.last_notification_sent_at
        portfolio = await session.scalar(
            select(Portfolio).where(Portfolio.owner_id == user_id))
        if portfolio:
            positions = await session.scalars(select(Position)
                .where(Position.portfolio_id == portfolio.id)).all()
            goals = await session.scalars(select(Goal)
                .where(Goal.portfolio_id == portfolio.id)).all()
            settings = await session.get(PortfolioSettings, portfolio.id)
        else:
            positions = []
            goals = []
            settings = None
        analysis = await session.scalar(select(AnalyticsEvent)
            .where(AnalyticsEvent.user_id == user_id,
                   AnalyticsEvent.event_name == "analysis.completed")
            .order_by(AnalyticsEvent.created_at.desc()))
        rebalance = await session.scalar(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.user_id == user_id,
                   AnalyticsEvent.event_name == "portfolio.rebalanced")
            .order_by(AnalyticsEvent.created_at.desc()))
        last_open = await session.scalar(select(AnalyticsEvent)
            .where(AnalyticsEvent.user_id == user_id,
                AnalyticsEvent.event_name == "portfolio.opened")
            .order_by(AnalyticsEvent.created_at.desc()))

        def days(event):
            if event is None:
                return None
            return (datetime.now(timezone.utc) - event.created_at).days

        ticker = None
        if analysis and analysis.event_data:
            ticker = analysis.event_data.get("ticker")
        return NotificationContext(
            user_id=user_id,
            has_portfolio=portfolio is not None,
            positions_count=len(positions),
            has_goal=len(goals) > 0,
            goals_count=len(goals),
            auto_invest=settings.auto_invest_enabled if settings else False,
            last_analysis_days=days(analysis),
            last_rebalance_days=days(rebalance),
            investment_style=profile.investment_style,
            portfolio_value=portfolio.total_value if portfolio else 0,
            first_analysis_done=profile.first_analysis_done,
            first_goal_done=profile.first_goal_done,
            first_rebalance_done=profile.first_rebalance_done,
            first_auto_done=profile.first_auto_invest_done,
            last_ticker=ticker,
            last_open_days=days(last_open))



async def get_notification(user_id: int):
    ctx = await build_context(user_id)
    if (ctx.last_notification_sent_at and (
        datetime.now(timezone.utc) - ctx.last_notification_sent_at).total_seconds() < 60 * 60 * 48):
        return None
    if not ctx.first_analysis_done:
        return random.choice(NEW)
    if not ctx.has_goal:
        return random.choice(GOALS)
    if not ctx.has_portfolio:
        return random.choice(PORTFOLIO)
    if (ctx.positions_count > 1
            and (ctx.last_rebalance_days is None or ctx.last_rebalance_days > 30)):
        return random.choice(REBALANCE)
    if not ctx.auto_invest:
        return random.choice(AUTO)
    if (ctx.last_open_days is not None
            and ctx.last_open_days > 30):
        return random.choice(INACTIVE)
    if ctx.last_analysis_days is not None and ctx.last_analysis_days > 14:
        return random.choice(INACTIVE)
    if ctx.last_ticker:
        return random.choice(TICKER).format(ticker=ctx.last_ticker)
    if (ctx.last_analysis_days is not None
            and ctx.investment_style == "growth"):
        return random.choice(GROWTH)
    if (ctx.last_analysis_days is not None
            and ctx.investment_style == "safe"):
        return random.choice(SAFE)

    return random.choice(BALANCED)