import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from typing import Dict, Any

from ProjectDataBase.models import Base, Owner, Category, Portfolio


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_session_maker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession)
    yield async_session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(async_session_maker):
    async with async_session_maker() as session:
        yield session

@pytest.fixture
def sample_stock_data():
    return {
        "ticker": "AAPL",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 2500000000000,
        "total_debt": 100000000000,
        "total_cash": 50000000000,
        "total_assets": 300000000000,
        "receivables": 30000000000,
        "revenue": 400000000000,
        "interest_income": 500000000,
        "financial_currency": "USD",
        "financials_updated_at": datetime.now(timezone.utc),
        "dividends": 0.5}


@pytest.fixture
def sample_etf_holdings():
    return [
        {"ticker": "AAPL", "weight": 0.15},
        {"ticker": "MSFT", "weight": 0.12},
        {"ticker": "GOOGL", "weight": 0.10},
        {"ticker": "AMZN", "weight": 0.08},
        {"ticker": "NVDA", "weight": 0.07},
        {"ticker": "META", "weight": 0.06},
        {"ticker": "BRK-B", "weight": 0.05},
        {"ticker": "JPM", "weight": 0.04},
        {"ticker": "V", "weight": 0.03},
        {"ticker": "JNJ", "weight": 0.03}]

@pytest.fixture
def sample_positions():
    return [
        {"ticker": "AAPL", "weight": 0.30, "quantity": 10, "average_price": 150.0},
        {"ticker": "MSFT", "weight": 0.25, "quantity": 8, "average_price": 300.0},
        {"ticker": "GOOGL", "weight": 0.20, "quantity": 5, "average_price": 120.0},
        {"ticker": "AMZN", "weight": 0.15, "quantity": 12, "average_price": 130.0},
        {"ticker": "NVDA", "weight": 0.10, "quantity": 3, "average_price": 450.0}]

@pytest.fixture
def sample_price_history():
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=252, freq='D')
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 252)
    prices = base_price * (1 + returns).cumprod()
    df = pd.DataFrame({
        "Date": dates,
        "Close": prices,
        "Open": prices * 0.99,
        "High": prices * 1.02,
        "Low": prices * 0.98,
        "Volume": np.random.randint(1000000, 10000000, 252)})
    df = df.set_index("Date")
    return df


@pytest.fixture
def sample_goals():
    return [
        {
            "id": 1,
            "portfolio_id": 1,
            "name": "Emergency Fund",
            "amount": 50000.0,
            "years": 3,
            "priority": 10,
            "compliance": "halal"},
        {
            "id": 2,
            "portfolio_id": 1,
            "name": "House Down Payment",
            "amount": 200000.0,
            "years": 7,
            "priority": 8,
            "compliance": "halal"}]


@pytest.fixture
def sample_user_profile():
    return {
        "user_id": 12345,
        "monthly_budget": 1000.0,
        "income": 5000.0,
        "investment_style": "balanced",
        "created_at": datetime.now(timezone.utc)}


@pytest.fixture
def mock_yf_ticker():
    ticker = Mock()
    ticker.history = Mock(return_value=None)
    ticker.info = {}
    ticker.fast_info = {"lastPrice": 150.0, "market_cap": 2500000000000}
    ticker.balance_sheet = pd.DataFrame({"Total Debt": [100000000000]})
    ticker.income_stmt = pd.DataFrame({"Total Revenue": [400000000000]})
    return ticker


@pytest.fixture
def mock_cache():
    cache = {}
    return cache


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.from_url = Mock(return_value=redis)


def create_mock_position(ticker: str, quantity: float, avg_price: float) -> Mock:
    position = Mock()
    position.ticker = ticker
    position.quantity = quantity
    position.average_price = avg_price
    return position


def create_mock_portfolio(id: int, cash: float, total_value: float) -> Mock:
    portfolio = Mock()
    portfolio.id = id
    portfolio.cash = cash
    portfolio.total_value = total_value
    return portfolio


def create_mock_owner(tg_id: int, id: int = 1) -> Mock:
    owner = Mock()
    owner.id = id
    owner.tg_id = tg_id
    return owner


async def setup_test_portfolio(db_session, tg_id: int = 12345) -> int:
    owner = Owner(tg_id=tg_id)
    db_session.add(owner)
    await db_session.flush()
    category = Category(name="Stocks")
    db_session.add(category)
    await db_session.flush()
    portfolio = Portfolio(
        owner_id=owner.id,
        cash=10000.0,
        total_value=10000.0)
    db_session.add(portfolio)
    await db_session.commit()
    return portfolio.id


def assert_valid_risk_metrics(metrics: Dict[str, Any]):
    assert metrics is not None
    assert "volatility" in metrics
    assert "risk_score" in metrics
    assert "risk_label" in metrics
    if metrics["volatility"] is not None:
        assert metrics["volatility"] >= 0
        assert metrics["volatility"] <= 100
    if metrics["risk_score"] is not None:
        assert 0 <= metrics["risk_score"] <= 100


def assert_valid_shariah_result(result: Dict[str, Any]):
    assert result is not None
    assert "status" in result
    assert "audit" in result
    assert "confidence" in result
    valid_statuses = [
        "СООТВЕТСТВУЕТ ШАРИАТУ ✅",
        "Скорее соответствует Шариату ⚠️",
        "Нужна дополнительная проверка ⚠️",
        "НЕ СООТВЕТСТВУЕТ ❌",
        "НЕДОСТАТОЧНО ДАННЫХ ⚠️"]
    assert result["status"] in valid_statuses
    if result["confidence"] is not None:
        assert 0 <= result["confidence"] <= 100



@pytest.fixture
def async_mock():
    return AsyncMock()


def run_async(coro):
    return asyncio.run(coro)