import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from sqlalchemy import select
from ProjectDataBase.models import Portfolio, Position, Category, MarketPrice, Transaction
from ProjectDataBase.backend import set_user, create_demo_portfolio, buy_position, delete_portfolio, execute_rebalance, \
    add_goal, get_goals, add_transaction, update_cash, get_user_portfolios, add_cash, sell_position, get_positions
from MainMetricsComputingFeatures.riskmanagement import calculate_portfolio_risk, calculate_diversification_score, \
    calculate_concentration_risk
from MainMetricsComputingFeatures.shariah import shariah_screen, calculate_portfolio_purification


@pytest.mark.integration
@pytest.mark.portfolio
class TestPortfolioWorkflowIntegration:
    @pytest.mark.asyncio
    async def test_complete_portfolio_analysis_workflow(self, db_session):
        await set_user(88888)
        portfolio_id = await create_demo_portfolio(88888, "Analysis Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        await buy_position(portfolio_id, "MSFT", 5, 300.0, category.id)
        await buy_position(portfolio_id, "GOOGL", 8, 120.0, category.id)
        for ticker, price in [("AAPL", 155.0), ("MSFT", 310.0), ("GOOGL", 125.0)]:
            market_price = MarketPrice(
                ticker=ticker,
                price=price,
                volume=1000000,
                market_cap=2500000000000)
            db_session.add(market_price)
        await db_session.commit()
        positions = await db_session.scalars(
            select(Position).where(Position.portfolio_id == portfolio_id))
        positions = positions.all()
        prices = {"AAPL": 155.0, "MSFT": 310.0, "GOOGL": 125.0}
        stocks_data = {
            "AAPL": {"sector": "Technology", "industry": "Consumer Electronics"},
            "MSFT": {"sector": "Technology", "industry": "Software"},
            "GOOGL": {"sector": "Technology", "industry": "Internet Services"}}
        positions_data = []
        total_value = 0
        for pos in positions:
            price = prices.get(pos.ticker, pos.average_price)
            value = pos.quantity * price
            total_value += value
            positions_data.append({
                "ticker": pos.ticker,
                "value": value,
                "quantity": pos.quantity,
                "avg_price": pos.average_price,
                "price": price})
        for pos in positions_data:
            pos["weight"] = pos["value"] / total_value
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_df = Mock()
            mock_df.empty = False
            mock_df.__getitem__ = Mock(return_value=Mock(pct_change=Mock(return_value=Mock(dropna=Mock(return_value=Mock(
                __len__=Mock(return_value=50)))))))
            mock_hist.return_value = mock_df
            risk = await calculate_portfolio_risk(positions_data)
            assert risk is not None
            assert "volatility" in risk
            assert "diversification" in risk
            assert "risk_score" in risk
        for ticker in ["AAPL", "MSFT", "GOOGL"]:
            stock = stocks_data[ticker]
            stock["ticker"] = ticker
            screening = await shariah_screen(stock)
            assert screening is not None
            assert "status" in screening
        purification = await calculate_portfolio_purification(positions_data, stocks_data)
        assert purification is not None
        assert "total_purification" in purification
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_portfolio_rebalancing_workflow(self, db_session):
        await set_user(88887)
        portfolio_id = await create_demo_portfolio(88887, "Rebalance Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 50, 150.0, category.id)
        await buy_position(portfolio_id, "MSFT", 10, 300.0, category.id)
        for ticker, price in [("AAPL", 155.0), ("MSFT", 310.0)]:
            market_price = MarketPrice(
                ticker=ticker,
                price=price,
                volume=1000000,
                market_cap=2500000000000)
            db_session.add(market_price)
        await db_session.commit()
        trades = [
            {"ticker": "AAPL", "action": "SELL", "amount": 2000.0},
            {"ticker": "MSFT", "action": "BUY", "amount": 2000.0}]
        success, message, executed = await execute_rebalance(portfolio_id, trades)
        assert success is True
        assert len(executed) > 0
        positions = await db_session.scalars(select(Position).where(Position.portfolio_id == portfolio_id))
        positions = positions.all()
        assert len(positions) == 2
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_goal_based_portfolio_workflow(self):
        await set_user(88886)
        portfolio_id = await create_demo_portfolio(88886, "Goal Test")
        goals = [
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
                "compliance": "halal"}]
        
        for goal in goals:
            await add_goal(goal)
        retrieved_goals = await get_goals(portfolio_id)
        assert len(retrieved_goals) == 2
        total_amount = sum(g["amount"] for g in retrieved_goals)
        assert total_amount == 130000.0
        sorted_goals = sorted(retrieved_goals, key=lambda x: x["priority"], reverse=True)
        assert sorted_goals[0]["priority"] >= sorted_goals[1]["priority"]
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_shariah_compliance_workflow(self, db_session):
        await set_user(88885)
        portfolio_id = await create_demo_portfolio(88885, "Shariah Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        await buy_position(portfolio_id, "MSFT", 10, 300.0, category.id)
        await buy_position(portfolio_id, "JPM", 5, 150.0, category.id)
        stocks_data = {
            "AAPL": {
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
                "financials_updated_at": datetime.now(timezone.utc)},
            "MSFT": {
                "ticker": "MSFT",
                "sector": "Technology",
                "industry": "Software",
                "market_cap": 2000000000000,
                "total_debt": 50000000000,
                "total_cash": 100000000000,
                "total_assets": 250000000000,
                "receivables": 40000000000,
                "revenue": 200000000000,
                "interest_income": 100000000,
                "financials_updated_at": datetime.now(timezone.utc)},
            "JPM": {
                "ticker": "JPM",
                "sector": "Financials",
                "industry": "Banks",
                "market_cap": 400000000000,
                "total_debt": 200000000000,
                "total_cash": 50000000000,
                "total_assets": 3000000000000,
                "receivables": 200000000000,
                "revenue": 100000000000,
                "interest_income": 50000000000,
                "financials_updated_at": datetime.now(timezone.utc)}}
        compliance_results = {}
        for ticker, stock in stocks_data.items():
            screening = await shariah_screen(stock)
            compliance_results[ticker] = screening["status"]
        assert len(compliance_results) == 3
        assert compliance_results["AAPL"] in [
            "СООТВЕТСТВУЕТ ШАРИАТУ ✅",
            "Скорее соответствует Шариату ⚠️"]
        assert compliance_results["MSFT"] in [
            "СООТВЕТСТВУЕТ ШАРИАТУ ✅",
            "Скорее соответствует Шариату ⚠️"]
        assert compliance_results["JPM"] is not None
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_risk_adjusted_workflow(self, db_session):
        await set_user(88884)
        portfolio_id = await create_demo_portfolio(88884, "Risk Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        await buy_position(portfolio_id, "MSFT", 10, 300.0, category.id)
        await buy_position(portfolio_id, "KO", 20, 60.0, category.id)
        positions = await db_session.scalars(select(Position).where(Position.portfolio_id == portfolio_id))
        positions = positions.all()
        positions_data = []
        for pos in positions:
            positions_data.append({
                "ticker": pos.ticker,
                "quantity": pos.quantity,
                "weight": 0.33})
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_df = Mock()
            mock_df.empty = False
            mock_hist.return_value = mock_df
            risk = await calculate_portfolio_risk(positions_data)
            assert risk is not None
            assert risk["volatility"] is not None or risk["volatility"] == 0
            assert risk["diversification"] is not None
            assert risk["risk_score"] is not None
        div_score = calculate_diversification_score(positions_data)
        assert div_score is not None
        assert div_score > 50
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_portfolio_performance_tracking_workflow(self, db_session):
        await set_user(88883)
        portfolio_id = await create_demo_portfolio(88883, "Performance Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        await add_transaction(portfolio_id, "AAPL", 10, 150.0, True)
        portfolio = await db_session.get(Portfolio, portfolio_id)
        initial_value = portfolio.total_value
        await buy_position(portfolio_id, "MSFT", 5, 300.0, category.id)
        await add_transaction(portfolio_id, "MSFT", 5, 300.0, True)
        await update_cash(portfolio_id, 12000.0)
        portfolio = await db_session.get(Portfolio, portfolio_id)
        updated_value = portfolio.total_value
        assert updated_value > initial_value
        transactions = await db_session.execute(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.created_at))
        transactions = transactions.scalars().all()
        assert len(transactions) == 2
        assert all(t.is_buy for t in transactions)
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_multi_portfolio_workflow(self):
        await set_user(88882)
        portfolio1_id = await create_demo_portfolio(88882, "Growth Portfolio")
        portfolio2_id = await create_demo_portfolio(88882, "Income Portfolio")
        portfolio3_id = await create_demo_portfolio(88882, "Retirement Portfolio")
        portfolios = await get_user_portfolios(88882)
        assert len(portfolios) == 3
        portfolio_ids = [p[1].id for p in portfolios]
        assert portfolio1_id in portfolio_ids
        assert portfolio2_id in portfolio_ids
        assert portfolio3_id in portfolio_ids
        demo_names = [p[0].name for p in portfolios]
        assert "Growth Portfolio" in demo_names
        assert "Income Portfolio" in demo_names
        assert "Retirement Portfolio" in demo_names
        for pid in [portfolio1_id, portfolio2_id, portfolio3_id]:
            await delete_portfolio(pid)
    
    @pytest.mark.asyncio
    async def test_portfolio_cash_flow_workflow(self, db_session):
        await set_user(88881)
        portfolio_id = await create_demo_portfolio(88881, "Cash Flow Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        portfolio = await db_session.get(Portfolio, portfolio_id)
        initial_cash = portfolio.cash
        await add_cash(portfolio_id, 5000.0)
        portfolio = await db_session.get(Portfolio, portfolio_id)
        assert portfolio.cash == initial_cash + 5000.0
        await buy_position(portfolio_id, "AAPL", 10, 150.0, category.id)
        portfolio = await db_session.get(Portfolio, portfolio_id)
        cash_after_buy = portfolio.cash
        success, _ = await sell_position(portfolio_id, "AAPL", 5)
        if success:
            portfolio = await db_session.get(Portfolio, portfolio_id)
            cash_after_sell = portfolio.cash
            assert cash_after_sell > cash_after_buy
        await delete_portfolio(portfolio_id)


@pytest.mark.integration
@pytest.mark.portfolio
class TestPortfolioEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_portfolio_workflow(self):
        await set_user(88880)
        portfolio_id = await create_demo_portfolio(88880, "Empty Test")
        positions = await get_positions(portfolio_id)
        assert len(positions) == 0
        risk = await calculate_portfolio_risk([])
        assert risk is None
        await delete_portfolio(portfolio_id)
    
    @pytest.mark.asyncio
    async def test_single_position_portfolio(self, db_session):
        await set_user(88879)
        portfolio_id = await create_demo_portfolio(88879, "Concentrated Test")
        category = Category(name="Stocks")
        db_session.add(category)
        await db_session.flush()
        await buy_position(portfolio_id, "AAPL", 100, 150.0, category.id)
        positions = await db_session.scalars(select(Position).where(Position.portfolio_id == portfolio_id))
        positions = positions.all()
        positions_data = [{
            "ticker": positions[0].ticker,
            "weight": 1.0}]
        concentration = calculate_concentration_risk(positions_data)
        diversification = calculate_diversification_score(positions_data)
        assert "🔴" in concentration
        assert diversification == 0.0
        await delete_portfolio(portfolio_id)