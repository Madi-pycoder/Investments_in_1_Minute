import pytest
from sqlalchemy import select
from ProjectDataBase.models import (
    Owner, Position, Transaction,
    Category, Demo, PortfolioSettings, UserProfileDB, MarketPrice)
from ProjectDataBase.backend import (
    set_user, create_demo_portfolio, buy_position, sell_position,
    add_transaction, get_portfolio, get_positions, get_goals,
    add_goal, update_goal, delete_goal, update_cash, delete_portfolio, login_demo_portfolio,
    recalculate_portfolio_value)


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_complete_user_portfolio_workflow(self, db_session):
        await set_user(99999)
        owner = await db_session.scalar(select(Owner).where(Owner.tg_id == 99999))
        assert owner is not None
        assert owner.tg_id == 99999
        portfolio_id = await create_demo_portfolio(99999, "Integration Test")
        assert portfolio_id is not None
        portfolio = await get_portfolio(portfolio_id)
        assert portfolio is not None
        assert portfolio.owner_id == owner.id
        assert portfolio.cash == 10000.0
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        positions = await get_positions(portfolio_id)
        assert len(positions) == 1
        assert positions[0].ticker == "AAPL"
        assert positions[0].quantity == 10
        await add_transaction(portfolio_id, "AAPL", 10, 150.0, True)
        transactions = await db_session.execute(select(Transaction).where(Transaction.portfolio_id == portfolio_id))
        transactions = transactions.scalars().all()
        assert len(transactions) == 1
        goal_data = {
            "portfolio_id": portfolio_id,
            "name": "Test Goal",
            "amount": 50000.0,
            "years": 5,
            "priority": 8,
            "compliance": "halal"}
        await add_goal(goal_data)
        goals = await get_goals(portfolio_id)
        assert len(goals) == 1
        assert goals[0]["name"] == "Test Goal"
        goal_id = goals[0]["id"]
        await update_goal(goal_id, amount=60000.0)
        goals = await get_goals(portfolio_id)
        assert goals[0]["amount"] == 60000.0
        await delete_goal(goal_id)
        goals = await get_goals(portfolio_id)
        assert len(goals) == 0
        success, message = await sell_position(portfolio_id, "AAPL", 5)
        assert success is True
        positions = await get_positions(portfolio_id)
        assert positions[0].quantity == 5
        await update_cash(portfolio_id, 15000.0)
        portfolio = await get_portfolio(portfolio_id)
        assert portfolio.cash == 15000.0
        await delete_portfolio(portfolio_id)
        portfolio = await get_portfolio(portfolio_id)
        assert portfolio is None
    
    @pytest.mark.asyncio
    async def test_portfolio_with_multiple_positions(self, db_session):
        await set_user(99998)
        portfolio_id = await create_demo_portfolio(99998, "Multi Position Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        await buy_position(portfolio_id, "MSFT", 5, 300.0, category.id)
        await buy_position(portfolio_id, "GOOGL", 8, 120.0, category.id)
        positions = await get_positions(portfolio_id)
        assert len(positions) == 3
        tickers = {p.ticker for p in positions}
        assert tickers == {"AAPL", "MSFT", "GOOGL"}
        portfolio = await get_portfolio(portfolio_id)
        assert portfolio.total_value > 10000.0
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_portfolio_settings_integration(self, db_session):
        await set_user(99997)
        portfolio_id = await create_demo_portfolio(99997, "Settings Test")
        settings = PortfolioSettings(
            portfolio_id=portfolio_id,
            monthly_budget=1000.0,
            risk_tolerance="medium",
            investment_style="balanced",
            auto_invest_enabled=True)
        db_session.add(settings)
        await db_session.commit()
        retrieved_settings = await db_session.get(PortfolioSettings, portfolio_id)
        assert retrieved_settings is not None
        assert retrieved_settings.monthly_budget == 1000.0
        assert retrieved_settings.auto_invest_enabled is True
        retrieved_settings.monthly_budget = 1500.0
        retrieved_settings.risk_tolerance = "high"
        await db_session.commit()
        await db_session.refresh(retrieved_settings)
        assert retrieved_settings.monthly_budget == 1500.0
        assert retrieved_settings.risk_tolerance == "high"
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_user_profile_integration(self, db_session):
        await set_user(99996)
        owner = await db_session.scalar(select(Owner).where(Owner.tg_id == 99996))
        profile = UserProfileDB(
            user_id=owner.tg_id,
            monthly_budget=1000.0,
            income=5000.0,
            investment_style="balanced")
        db_session.add(profile)
        await db_session.commit()
        retrieved_profile = await db_session.get(UserProfileDB, owner.tg_id)
        assert retrieved_profile is not None
        assert retrieved_profile.monthly_budget == 1000.0
        assert retrieved_profile.investment_style == "balanced"
        retrieved_profile.monthly_budget = 1500.0
        retrieved_profile.investment_style = "aggressive"
        await db_session.commit()
        await db_session.refresh(retrieved_profile)
        assert retrieved_profile.monthly_budget == 1500.0
        assert retrieved_profile.investment_style == "aggressive"
    
    @pytest.mark.asyncio
    async def test_transaction_history_integration(self, db_session):
        await set_user(99995)
        portfolio_id = await create_demo_portfolio(99995, "Transaction Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        await add_transaction(portfolio_id, "AAPL", 10, 150.0, True)
        await buy_position(portfolio_id, "MSFT", 5, 300.0, category.id)
        await add_transaction(portfolio_id, "MSFT", 5, 300.0, True)
        success, _ = await sell_position(portfolio_id, "AAPL", 5)
        if success:
            await add_transaction(portfolio_id, "AAPL", 5, 155.0, False)
        transactions = await db_session.execute(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.created_at))
        transactions = transactions.scalars().all()
        assert len(transactions) >= 2
        buy_transactions = [t for t in transactions if t.is_buy]
        assert len(buy_transactions) >= 2
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_goal_management_integration(self):
        await set_user(99994)
        portfolio_id = await create_demo_portfolio(99994, "Goal Test")
        goals_data = [
            {
                "portfolio_id": portfolio_id,
                "name": "Emergency Fund",
                "amount": 30000.0,
                "years": 2,
                "priority": 10,
                "compliance": "halal"},
            {
                "portfolio_id": portfolio_id,
                "name": "House Down Payment",
                "amount": 100000.0,
                "years": 7,
                "priority": 8,
                "compliance": "halal"},
            {
                "portfolio_id": portfolio_id,
                "name": "Retirement",
                "amount": 500000.0,
                "years": 25,
                "priority": 6,
                "compliance": "halal"}]
        for goal_data in goals_data:
            await add_goal(goal_data)
        goals = await get_goals(portfolio_id)
        assert len(goals) == 3
        await update_goal(goals[0]["id"], priority=9)
        goals = await get_goals(portfolio_id)
        assert goals[0]["priority"] == 9
        await delete_goal(goals[1]["id"])
        goals = await get_goals(portfolio_id)
        assert len(goals) == 2
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_demo_portfolio_integration(self, db_session):
        await set_user(99993)
        portfolio_id = await create_demo_portfolio(99993, "Demo Integration")
        demo = await db_session.scalar(select(Demo).where(Demo.portfolio_id == portfolio_id))
        assert demo is not None
        assert demo.name == "Demo Integration"
        portfolio, message = await login_demo_portfolio(99993, "Demo Integration")
        assert portfolio is not None
        assert portfolio.id == portfolio_id
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_portfolio_value_recalculation(self, db_session):
        await set_user(99992)
        portfolio_id = await create_demo_portfolio(99992, "Value Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        market_price = MarketPrice(
            ticker="AAPL",
            price=150.0,
            volume=1000000,
            market_cap=2500000000000)
        db_session.add(market_price)
        await db_session.commit()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        await recalculate_portfolio_value(portfolio_id)
        portfolio = await get_portfolio(portfolio_id)
        assert portfolio.total_value > portfolio.cash
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_cascade_delete_portfolio(self, db_session):
        await set_user(99991)
        portfolio_id = await create_demo_portfolio(99991, "Cascade Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        await add_transaction(portfolio_id, "AAPL", 10, 150.0, True)
        goal_data = {
            "portfolio_id": portfolio_id,
            "name": "Test Goal",
            "amount": 50000.0,
            "years": 5,
            "priority": 8,
            "compliance": "halal"}
        await add_goal(goal_data)
        await delete_portfolio(portfolio_id)
        portfolio = await get_portfolio(portfolio_id)
        assert portfolio is None
        positions = await get_positions(portfolio_id)
        assert len(positions) == 0
        goals = await get_goals(portfolio_id)
        assert len(goals) == 0
        demo = await db_session.scalar(select(Demo).where(Demo.portfolio_id == portfolio_id))
        assert demo is None


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseConstraints:
    @pytest.mark.asyncio
    async def test_unique_tg_id_constraint(self, db_session):
        await set_user(99990)
        await set_user(99990)
        owners = await db_session.execute(select(Owner).where(Owner.tg_id == 99990))
        owners = owners.scalars().all()
        assert len(owners) == 1
    
    @pytest.mark.asyncio
    async def test_category_unique_name(self, db_session):
        category1 = Category(name="UniqueTest")
        db_session.add(category1)
        await db_session.commit()
        category2 = Category(name="UniqueTest")
        db_session.add(category2)
        with pytest.raises(Exception):
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, db_session):
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        position = Position(
            portfolio_id=99999,
            ticker="AAPL",
            quantity=10,
            average_price=150.0,
            category_id=category.id)
        db_session.add(position)
        with pytest.raises(Exception):
            await db_session.commit()