from datetime import datetime, date
from config import DATABASE_URL
from sqlalchemy import (BigInteger, DateTime, Date, String, Integer,
    Float, Boolean, ForeignKey, UniqueConstraint, Index, func, select)
from sqlalchemy.ext.asyncio import (create_async_engine, async_sessionmaker, AsyncAttrs,)
from sqlalchemy.orm import (DeclarativeBase, mapped_column, Mapped)
from sqlalchemy.dialects.postgresql import JSONB
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
class Base(AsyncAttrs, DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = "owners"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger,unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Demo(Base):
    __tablename__ = "demos"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50),unique=True)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id"),index=True)
    cash: Mapped[float] = mapped_column(Float)
    total_value: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), index=True)


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (Index("ix_position_portfolio", "portfolio_id"),
        Index("ix_position_ticker", "ticker"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    ticker: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float)
    average_price: Mapped[float] = mapped_column(Float)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transaction_portfolio", "portfolio_id"),
        Index("ix_transaction_ticker", "ticker"),
        Index("ix_transaction_created", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    ticker: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    is_buy: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (Index("ix_goal_portfolio", "portfolio_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id",
        ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    years: Mapped[int] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer)
    compliance: Mapped[str] = mapped_column(String)


class MarketAsset(Base):
    __tablename__ = "market_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), index=True)


class MarketPrice(Base):
    __tablename__ = "market_prices"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20),unique=True,index=True)
    price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    market_cap: Mapped[float] = mapped_column(Float)
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
    server_default=func.now(), index=True)


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"
    __table_args__ = (UniqueConstraint("ticker", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[date] = mapped_column(Date)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


class ShariahScreen(Base):
    __tablename__ = "shariah_screens"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    standard: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(50))
    score: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    audit_json: Mapped[str] = mapped_column(JSONB)
    financials_updated_at: Mapped[datetime] = mapped_column(DateTime)
    screened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
    server_default=func.now(), index=True)


class StockFundamentals(Base):
    __tablename__ = "stock_fundamentals"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(150), nullable=True)
    quote_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
        server_default=func.now(), onupdate=func.now(), index=True)
    total_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cash: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    receivables: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    financial_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)


class UserProfileDB(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("owners.tg_id"), primary_key=True)
    monthly_budget: Mapped[float] = mapped_column(Float, default=0)
    income: Mapped[float | None] = mapped_column(Float, nullable=True)
    investment_style: Mapped[str] = mapped_column(String(30), default="balanced")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
        server_default=func.now())
    first_goal_done: Mapped[bool] = mapped_column(Boolean, default=False)
    first_analysis_done: Mapped[bool] = mapped_column(Boolean, default=False)
    first_rebalance_done: Mapped[bool] = mapped_column(Boolean, default=False)
    first_auto_invest_done: Mapped[bool] = mapped_column(Boolean, default=False)
    welcome_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    welcome_seen: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    last_notification_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event_name: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str | None] = mapped_column(String(30), index=True, nullable=True)
    event_version: Mapped[int] = mapped_column(Integer, default=1)
    source_attribution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True)


class DailyAnalyticsSnapshot(Base):
    __tablename__ = "daily_analytics"
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    dau: Mapped[int] = mapped_column(Integer)
    portfolio_opens: Mapped[int] = mapped_column(Integer)
    auto_invest_execs: Mapped[int] = mapped_column(Integer)
    avg_response_time: Mapped[float] = mapped_column(Float)
    retention_d1: Mapped[float] = mapped_column(Float)
    retention_d7: Mapped[float] = mapped_column(Float)
    activation_rate: Mapped[float] = mapped_column(Float, default=0)
    rebalance_adoption: Mapped[float] = mapped_column(Float, default=0)
    ai_engagement_rate: Mapped[float] = mapped_column(Float, default=0)
    auto_invest_conversion: Mapped[float] = mapped_column(Float, default=0)
    avg_portfolio_size: Mapped[float] = mapped_column(Float, default=0)
    avg_goals_per_user: Mapped[float] = mapped_column(Float, default=0)
    churn_risk_rate: Mapped[float] = mapped_column(Float, default=0)


class FunnelSnapshot(Base):
    __tablename__ = "funnels"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    step_name: Mapped[str] = mapped_column(String(100), index=True)
    users_entered: Mapped[int] = mapped_column(Integer, default=0)
    users_completed: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[float] = mapped_column(Float, default=0)
    avg_completion_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)


class PortfolioSettings(Base):
    __tablename__ = "portfolio_settings"
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), primary_key=True)
    monthly_budget: Mapped[float] = mapped_column(Float, default=0)
    risk_tolerance: Mapped[str] = mapped_column(String(20), default="medium")
    investment_style: Mapped[str] = mapped_column(String(30), default="balanced")
    auto_invest_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_auto_invest: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_auto_invest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())



class UserReview(Base):
    __tablename__ = "user_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("owners.tg_id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    admin_note: Mapped[str | None] = mapped_column(String(300), nullable=True)


class ReferralCode(Base):
    __tablename__ = "referral_codes"
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("owners.tg_id"),
        primary_key=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    reward_given: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
        server_default=func.now())


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(primary_key=True)
    inviter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("owners.tg_id"), index=True)
    invited_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("owners.tg_id"), unique=True)
    rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GrowthPromoState(Base):
    __tablename__ = "growth_promo_states"
    __table_args__ = (Index("ix_growth_promo_user_type", "user_id", "promo_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("owners.tg_id"), index=True)
    promo_type: Mapped[str] = mapped_column(String(50), index=True)
    last_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    show_count: Mapped[int] = mapped_column(Integer, default=0)
    user_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    content_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserGamification(Base):
    __tablename__ = "user_gamification"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("owners.tg_id"), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[date | None] = mapped_column(Date, nullable=0)
    analysis_count: Mapped[int] = mapped_column(Integer, default=0)
    buy_count: Mapped[int] = mapped_column(Integer, default=0)
    sell_count: Mapped[int] = mapped_column(Integer, default=0)
    portfolio_count: Mapped[int] = mapped_column(Integer, default=0)
    goal_count: Mapped[int] = mapped_column(Integer, default=0)
    achievements_count: Mapped[int] = mapped_column(Integer, default=0)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("owners.tg_id"), index=True)
    achievement: Mapped[str] = mapped_column(String(80))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = UniqueConstraint("user_id", "achievement")


async def seed_categories():
    async with async_session() as session:
        stocks = await session.scalar(
            select(Category).where(Category.name == "Stocks"))
        if not stocks:
            session.add(Category(name="Stocks"))
            await session.commit()