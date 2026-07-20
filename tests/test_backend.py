import pytest
import time
from unittest.mock import patch
from sqlalchemy import select
from ProjectDataBase.models import Portfolio, Owner, Category, Position, Demo, Transaction, Goal, MarketPrice
from ProjectDataBase.backend import (
    make_portfolio_cache_key,
    get_portfolio_data_cached,
    preload_diagnosis,
    get_diagnosis_cached,
    set_user,
    create_demo_portfolio,
    buy_position,
    sell_position,
    add_transaction,
    get_portfolio,
    get_positions,
    get_user_portfolios,
    login_demo_portfolio,
    update_cash,
    delete_portfolio,
    execute_rebalance,
    get_goals,
    add_goal,
    update_goal,
    delete_goal,
    add_cash,
    deposit_monthly_budget,
    portfolio_data_cache,
    diagnosis_cache)


@pytest.mark.unit
@pytest.mark.database
class TestCacheFunctions:
    def test_make_portfolio_cache_key(self):
        positions = [
            {"ticker": "AAPL", "weight": 0.5},
            {"ticker": "MSFT", "weight": 0.5}]
        key = make_portfolio_cache_key(positions)
        assert isinstance(key, tuple)
        assert len(key) == 2
    
    def test_get_portfolio_data_cached_hit(self):
        portfolio_data_cache[1] = {
            "data": {"test": "data"},
            "ts": time.time()}
        result = get_portfolio_data_cached(1)
        assert result is not None
        assert result["test"] == "data"
    
    def test_get_portfolio_data_cached_miss(self):
        result = get_portfolio_data_cached(999)
        assert result is None
    
    def test_get_portfolio_data_cached_expired(self):
        portfolio_data_cache[1] = {
            "data": {"test": "data"},
            "ts": time.time() - 100}
        result = get_portfolio_data_cached(1)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_preload_diagnosis(self):
        data = {"test": "data"}
        with patch('ProjectDataBase.backend.get_cached_metrics') as mock_metrics:
            mock_metrics.return_value = {"metrics": "data"}
            await preload_diagnosis(1, data)
            assert 1 in diagnosis_cache
    
    def test_get_diagnosis_cached_hit(self):
        diagnosis_cache[1] = {
            "data": {"diagnosis": "data"},
            "ts": time.time()}
        result = get_diagnosis_cached(1)
        assert result is not None
        assert result["diagnosis"] == "data"
    
    def test_get_diagnosis_cached_miss(self):
        result = get_diagnosis_cached(999)
        assert result is None


@pytest.mark.unit
@pytest.mark.database
class TestUserOperations:
    @pytest.mark.asyncio
    async def test_set_user_new(self, db_session):
        await set_user(12345)
        user = await db_session.scalar(select(Owner).where(Owner.tg_id == 12345))
        assert user is not None
        assert user.tg_id == 12345
    
    @pytest.mark.asyncio
    async def test_set_user_existing(self, db_session):
        user = Owner(tg_id=12345)
        db_session.add(user)
        await db_session.commit()
        await set_user(12345)


@pytest.mark.unit
@pytest.mark.database
class TestPortfolioOperations:
    @pytest.mark.asyncio
    async def test_create_demo_portfolio(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio_id = await create_demo_portfolio(12345, "Test Demo")
        assert portfolio_id is not None
        assert isinstance(portfolio_id, int)
    
    @pytest.mark.asyncio
    async def test_create_demo_portfolio_no_user(self):
        portfolio_id = await create_demo_portfolio(99999, "Test Demo")
        assert portfolio_id is None
    
    @pytest.mark.asyncio
    async def test_get_portfolio(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=1000.0, total_value=1000.0)
        db_session.add(portfolio)
        await db_session.commit()
        result = await get_portfolio(portfolio.id)
        assert result is not None
        assert result.id == portfolio.id
    
    @pytest.mark.asyncio
    async def test_get_portfolio_not_found(self):
        result = await get_portfolio(99999)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_positions(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=1000.0, total_value=1000.0)
        db_session.add(portfolio)
        await db_session.flush()
        position = Position(
            portfolio_id=portfolio.id,
            ticker="AAPL",
            quantity=10,
            average_price=150.0,
            category_id=category.id)
        db_session.add(position)
        await db_session.commit()
        positions = await get_positions(portfolio.id)
        assert len(positions) == 1
        assert positions[0].ticker == "AAPL"
    
    @pytest.mark.asyncio
    async def test_update_cash(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=1000.0, total_value=1000.0)
        db_session.add(portfolio)
        await db_session.commit()
        await update_cash(portfolio.id, 2000.0)
        await db_session.refresh(portfolio)
        assert portfolio.cash == 2000.0
    
    @pytest.mark.asyncio
    async def test_delete_portfolio(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=1000.0, total_value=1000.0)
        db_session.add(portfolio)
        await db_session.flush()
        demo = Demo(name="Test", portfolio_id=portfolio.id)
        db_session.add(demo)
        await db_session.commit()
        await delete_portfolio(portfolio.id)
        result = await get_portfolio(portfolio.id)
        assert result is None


@pytest.mark.unit
@pytest.mark.database
class TestPositionOperations:
    @pytest.mark.asyncio
    async def test_buy_position_new(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.commit()
        await buy_position(portfolio.id, "AAPL", 10, 150.0, category.id)
        positions = await get_positions(portfolio.id)
        assert len(positions) == 1
        assert positions[0].ticker == "AAPL"
        assert positions[0].quantity == 10
    
    @pytest.mark.asyncio
    async def test_buy_position_existing(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.flush()
        position = Position(
            portfolio_id=portfolio.id,
            ticker="AAPL",
            quantity=10,
            average_price=150.0,
            category_id=category.id)
        db_session.add(position)
        await db_session.commit()
        await buy_position(portfolio.id, "AAPL", 5, 160.0, category.id)
        positions = await get_positions(portfolio.id)
        assert positions[0].quantity == 15
    
    @pytest.mark.asyncio
    async def test_buy_position_no_category(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.commit()
        with pytest.raises(ValueError):
            await buy_position(portfolio.id, "AAPL", 10, 150.0, None)
    
    @pytest.mark.asyncio
    async def test_sell_position(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.flush()
        position = Position(
            portfolio_id=portfolio.id,
            ticker="AAPL",
            quantity=10,
            average_price=150.0,
            category_id=category.id)
        db_session.add(position)
        await db_session.commit()
        success, message = await sell_position(portfolio.id, "AAPL", 5)
        assert success is True
        positions = await get_positions(portfolio.id)
        assert positions[0].quantity == 5
    
    @pytest.mark.asyncio
    async def test_sell_position_not_found(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.commit()
        success, message = await sell_position(portfolio.id, "AAPL", 5)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_sell_position_insufficient(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.flush()
        position = Position(
            portfolio_id=portfolio.id,
            ticker="AAPL",
            quantity=10,
            average_price=150.0,
            category_id=category.id)
        db_session.add(position)
        await db_session.commit()
        success, message = await sell_position(portfolio.id, "AAPL", 15)
        assert success is False


@pytest.mark.unit
@pytest.mark.database
class TestTransactionOperations:
    @pytest.mark.asyncio
    async def test_add_transaction(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.commit()
        await add_transaction(portfolio.id, "AAPL", 10, 150.0, True)
        result = await db_session.execute(
            select(Transaction).where(Transaction.portfolio_id == portfolio.id))
        transactions = result.scalars().all()
        assert len(transactions) == 1
        assert transactions[0].ticker == "AAPL"
        assert transactions[0].is_buy is True


@pytest.mark.unit
@pytest.mark.database
class TestGoalOperations:
    @pytest.mark.asyncio
    async def test_add_goal(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.commit()
        goal_data = {
            "portfolio_id": portfolio.id,
            "name": "Test Goal",
            "amount": 50000.0,
            "years": 5,
            "priority": 8,
            "compliance": "halal"}
        await add_goal(goal_data)
        goals = await get_goals(portfolio.id)
        assert len(goals) == 1
        assert goals[0]["name"] == "Test Goal"
    
    @pytest.mark.asyncio
    async def test_get_goals(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.flush()
        goal = Goal(
            portfolio_id=portfolio.id,
            name="Test Goal",
            amount=50000.0,
            years=5,
            priority=8,
            compliance="halal")
        db_session.add(goal)
        await db_session.commit()
        goals = await get_goals(portfolio.id)
        assert len(goals) == 1
    
    @pytest.mark.asyncio
    async def test_update_goal(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.flush()
        goal = Goal(
            portfolio_id=portfolio.id,
            name="Test Goal",
            amount=50000.0,
            years=5,
            priority=8,
            compliance="halal")
        db_session.add(goal)
        await db_session.commit()
        await update_goal(goal.id, amount=60000.0)
        await db_session.refresh(goal)
        assert goal.amount == 60000.0
    
    @pytest.mark.asyncio
    async def test_delete_goal(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.flush()
        goal = Goal(
            portfolio_id=portfolio.id,
            name="Test Goal",
            amount=50000.0,
            years=5,
            priority=8,
            compliance="halal")
        db_session.add(goal)
        await db_session.commit()
        await delete_goal(goal.id)
        goals = await get_goals(portfolio.id)
        assert len(goals) == 0


@pytest.mark.unit
@pytest.mark.database
class TestCashOperations:
    @pytest.mark.asyncio
    async def test_add_cash(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=1000.0, total_value=1000.0)
        db_session.add(portfolio)
        await db_session.commit()
        result = await add_cash(portfolio.id, 500.0)
        assert result is True
        await db_session.refresh(portfolio)
        assert portfolio.cash == 1500.0
    
    @pytest.mark.asyncio
    async def test_deposit_monthly_budget(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=1000.0, total_value=1000.0)
        db_session.add(portfolio)
        await db_session.commit()
        result = await deposit_monthly_budget(portfolio.id, 500.0)
        assert result is True
        await db_session.refresh(portfolio)
        assert portfolio.cash == 1500.0


@pytest.mark.unit
@pytest.mark.database
class TestRebalanceExecution:
    @pytest.mark.asyncio
    async def test_execute_rebalance(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=5000.0, total_value=5000.0)
        db_session.add(portfolio)
        await db_session.flush()
        market_price = MarketPrice(ticker="AAPL", price=150.0, volume=1000000, market_cap=2500000000000)
        db_session.add(market_price)
        await db_session.commit()
        trades = [{"ticker": "AAPL", "action": "BUY", "amount": 1000.0}]
        success, message, executed = await execute_rebalance(portfolio.id, trades)
        assert success is True
        assert len(executed) > 0


@pytest.mark.unit
@pytest.mark.database
class TestUserPortfolios:
    @pytest.mark.asyncio
    async def test_get_user_portfolios(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=1000.0, total_value=1000.0)
        db_session.add(portfolio)
        await db_session.flush()
        demo = Demo(name="Test Demo", portfolio_id=portfolio.id)
        db_session.add(demo)
        await db_session.commit()
        portfolios = await get_user_portfolios(12345)
        assert len(portfolios) == 1
    
    @pytest.mark.asyncio
    async def test_get_user_portfolios_no_user(self):
        portfolios = await get_user_portfolios(99999)
        assert len(portfolios) == 0


@pytest.mark.unit
@pytest.mark.database
class TestDemoPortfolio:
    @pytest.mark.asyncio
    async def test_login_demo_portfolio(self, db_session):
        owner = Owner(tg_id=12345)
        db_session.add(owner)
        await db_session.flush()
        portfolio = Portfolio(owner_id=owner.id, cash=10000.0, total_value=10000.0)
        db_session.add(portfolio)
        await db_session.flush()
        demo = Demo(name="Test Demo", portfolio_id=portfolio.id)
        db_session.add(demo)
        await db_session.commit()
        portfolio, message = await login_demo_portfolio(12345, "Test Demo")
        assert portfolio is not None
        assert "Успешный вход" in message
    
    @pytest.mark.asyncio
    async def test_login_demo_portfolio_not_found(self):
        portfolio, message = await login_demo_portfolio(12345, "Nonexistent")
        assert portfolio is None
        assert "не найден" in message.lower()