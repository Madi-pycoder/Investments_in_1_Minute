import pytest
import numpy as np
from unittest.mock import Mock, patch
from Portfolio_info.portfolio_compute import (
    get_auto_invest_monthly,
    build_positions_data,
    get_top_movers,
    compute_sector_exposure,
    compute_sector_fast,
    compute_rebalance,
    compute_light_metrics,
    compute_portfolio_metrics)


@pytest.mark.unit
@pytest.mark.portfolio
class TestAutoInvest:
    def test_get_auto_invest_monthly(self):
        auto_invest = [
            {"amount": 500.0, "ticker": "AAPL"},
            {"amount": 300.0, "ticker": "MSFT"},
            {"amount": 200.0, "ticker": "GOOGL"}]
        result = get_auto_invest_monthly(auto_invest)
        assert result == 1000.0
    
    def test_get_auto_invest_monthly_empty(self):
        result = get_auto_invest_monthly([])
        assert result == 0.0


@pytest.mark.unit
@pytest.mark.portfolio
class TestPositionsData:
    def test_build_positions_data(self, sample_positions):
        positions = [Mock(ticker=p["ticker"], quantity=p["quantity"], average_price=p["average_price"]) 
                     for p in sample_positions]
        prices = {p["ticker"]: 150.0 for p in sample_positions}
        data = {
            "positions": positions,
            "stocks_batch": {p["ticker"]: {} for p in sample_positions}}
        positions_data, total_value = build_positions_data(positions, prices, data)
        assert positions_data is not None
        assert len(positions_data) == len(sample_positions)
        assert total_value > 0
        for pos in positions_data:
            assert "weight" in pos
            assert 0 <= pos["weight"] <= 1
    
    def test_build_positions_data_with_missing_price(self, sample_positions):
        positions = [Mock(ticker=p["ticker"], quantity=p["quantity"], average_price=p["average_price"]) 
                     for p in sample_positions]
        prices = {}
        data = {
            "positions": positions,
            "stocks_batch": {p["ticker"]: {} for p in sample_positions}}
        positions_data, total_value = build_positions_data(positions, prices, data)
        assert positions_data is not None
    
    def test_build_positions_data_pnl_calculation(self):
        positions = [Mock(ticker="AAPL", quantity=10, average_price=100.0)]
        prices = {"AAPL": 150.0}
        data = {
            "positions": positions,
            "stocks_batch": {"AAPL": {}}}
        positions_data, total_value = build_positions_data(positions, prices, data)
        assert positions_data[0]["pnl_pct"] == 50.0
        assert positions_data[0]["pnl_abs"] == 500.0


@pytest.mark.unit
@pytest.mark.portfolio
class TestTopMovers:
    def test_get_top_movers(self):
        positions_data = [
            {"ticker": "AAPL", "pnl_pct": 25.0},
            {"ticker": "MSFT", "pnl_pct": 15.0},
            {"ticker": "GOOGL", "pnl_pct": -10.0},
            {"ticker": "AMZN", "pnl_pct": -20.0},
            {"ticker": "NVDA", "pnl_pct": 30.0}]
        gainers, losers = get_top_movers(positions_data)
        assert len(gainers) == 3
        assert len(losers) == 3
        assert gainers[0]["pnl_pct"] >= gainers[1]["pnl_pct"]
        assert gainers[1]["pnl_pct"] >= gainers[2]["pnl_pct"]
        assert losers[0]["pnl_pct"] <= losers[1]["pnl_pct"]
        assert losers[1]["pnl_pct"] <= losers[2]["pnl_pct"]
    
    def test_get_top_movers_insufficient_data(self):
        positions_data = [{"ticker": "AAPL", "pnl_pct": 25.0}]
        gainers, losers = get_top_movers(positions_data)
        assert len(gainers) == 1
        assert len(losers) == 1


@pytest.mark.unit
@pytest.mark.portfolio
class TestSectorExposure:
    def test_compute_sector_exposure(self):
        positions = [
            Mock(ticker="AAPL", quantity=10),
            Mock(ticker="MSFT", quantity=10),
            Mock(ticker="JPM", quantity=10)]
        prices = {"AAPL": 150.0, "MSFT": 300.0, "JPM": 150.0}
        stocks = {
            "AAPL": {"sector": "Technology"},
            "MSFT": {"sector": "Technology"},
            "JPM": {"sector": "Financials"}}
        sector_exposure, top_sector, top_weight = compute_sector_exposure(
            positions, prices, stocks, 6000.0)
        assert sector_exposure is not None
        assert "Technology" in sector_exposure
        assert "Financials" in sector_exposure
        assert top_sector == "Technology"
        assert top_weight > 0.5
    
    def test_compute_sector_fast(self):
        positions = [
            Mock(ticker="AAPL", quantity=10),
            Mock(ticker="MSFT", quantity=10)]
        prices = {"AAPL": 150.0, "MSFT": 300.0}
        stocks = {
            "AAPL": {"sector": "Technology"},
            "MSFT": {"sector": "Technology"}}
        sector = compute_sector_fast(positions, prices, stocks)
        assert sector is not None
        assert "Technology" in sector
        assert sector["Technology"] == 1.0  # 100% Technology
    
    def test_compute_sector_fast_missing_sector(self):
        positions = [Mock(ticker="AAPL", quantity=10)]
        prices = {"AAPL": 150.0}
        stocks = {"AAPL": {}}
        sector = compute_sector_fast(positions, prices, stocks)
        assert sector is not None
        assert "Other" in sector


@pytest.mark.unit
@pytest.mark.portfolio
class TestRebalance:
    @pytest.mark.asyncio
    async def test_compute_rebalance(self, sample_positions):
        positions_data = [
            {"ticker": p["ticker"], "weight": p["weight"], "value": 1000.0}
            for p in sample_positions]
        stocks = {p["ticker"]: {} for p in sample_positions}
        with patch('Portfolio_info.portfolio_compute.optimize_shariah_portfolio') as mock_opt:
            mock_opt.return_value = {
                "AAPL": 0.25,
                "MSFT": 0.25,
                "GOOGL": 0.25,
                "AMZN": 0.25}
            with patch('Portfolio_info.portfolio_compute.calculate_rebalance') as mock_calc:
                mock_calc.return_value = {
                    "trades": [],
                    "expected_cost": 0.0}
                result = await compute_rebalance(positions_data, stocks, 5000.0)
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_compute_rebalance_no_weights(self, sample_positions):
        positions_data = [
            {"ticker": p["ticker"], "weight": p["weight"], "value": 1000.0}
            for p in sample_positions]
        stocks = {p["ticker"]: {} for p in sample_positions}
        with patch('Portfolio_info.portfolio_compute.optimize_shariah_portfolio') as mock_opt:
            mock_opt.return_value = None
            result = await compute_rebalance(positions_data, stocks, 5000.0)
            assert result is None


@pytest.mark.unit
@pytest.mark.portfolio
class TestLightMetrics:
    @pytest.mark.asyncio
    async def test_compute_light_metrics(self, sample_positions):
        positions = [Mock(ticker=p["ticker"], quantity=p["quantity"], average_price=p["average_price"]) 
                     for p in sample_positions]
        prices = {p["ticker"]: 150.0 for p in sample_positions}
        stocks = {
            p["ticker"]: {
                "sector": "Technology",
                "industry": "Software"}
            for p in sample_positions}
        portfolio = Mock(cash=1000.0)
        data = {
            "positions": positions,
            "prices_dict": prices,
            "stocks_batch": stocks,
            "portfolio": portfolio,
            "portfolio_id": 1,
            "goals": []}
        with patch('Portfolio_info.portfolio_compute.shariah_screen') as mock_screen:
            mock_screen.return_value = {"status": "СООТВЕТСТВУЕТ ШАРИАТУ ✅"}
            with patch('Portfolio_info.portfolio_compute.calculate_portfolio_risk') as mock_risk:
                mock_risk.return_value = {
                    "volatility": 20.0,
                    "diversification": 75.0,
                    "concentration": "Хорошая Диверсификация 🟢",
                    "risk_score": 80}
                with patch('Portfolio_info.portfolio_compute.get_effective_monthly_budget') as mock_budget:
                    mock_budget.return_value = 1000.0
                    with patch('Portfolio_info.portfolio_compute.get_portfolio_profile') as mock_profile:
                        mock_profile.return_value = Mock(cash=1000.0)
                        with patch('Portfolio_info.portfolio_compute.simulate_multiple_goals') as mock_goals:
                            mock_goals.return_value = []
                            with patch('Portfolio_info.portfolio_compute.run_what_if_scenarios') as mock_scenarios:
                                mock_scenarios.return_value = []
                                result = await compute_light_metrics(data)
                                assert result is not None
                                assert "positions_data" in result
                                assert "total_value" in result
                                assert "sector_exposure" in result


@pytest.mark.unit
@pytest.mark.portfolio
class TestPortfolioMetrics:
    @pytest.mark.asyncio
    async def test_compute_portfolio_metrics(self, sample_positions):
        positions = [Mock(ticker=p["ticker"], quantity=p["quantity"], average_price=p["average_price"]) 
                     for p in sample_positions]
        prices = {p["ticker"]: 150.0 for p in sample_positions}
        stocks = {
            p["ticker"]: {
                "sector": "Technology",
                "industry": "Software"} for p in sample_positions}
        portfolio = Mock(cash=1000.0, id=1)
        data = {
            "positions": positions,
            "prices_dict": prices,
            "stocks_batch": stocks,
            "portfolio": portfolio,
            "portfolio_id": 1,
            "goals": []}
        with patch('Portfolio_info.portfolio_compute.shariah_screen') as mock_screen:
            mock_screen.return_value = {"status": "СООТВЕТСТВУЕТ ШАРИАТУ ✅"}
            with patch('Portfolio_info.portfolio_compute.calculate_portfolio_risk') as mock_risk:
                mock_risk.return_value = {
                    "volatility": 20.0,
                    "diversification": 75.0,
                    "concentration": "Хорошая Диверсификация 🟢",
                    "risk_score": 80}
                with patch('Portfolio_info.portfolio_compute.compute_async_insights') as mock_async:
                    mock_async.return_value = (mock_risk.return_value, {}, {})
                    with patch('Portfolio_info.portfolio_compute.compute_rebalance') as mock_rebalance:
                        mock_rebalance.return_value = None
                        with patch('Portfolio_info.portfolio_compute.calculate_portfolio_purification') as mock_purification:
                            mock_purification.return_value = {
                                "total_purification": 0.0,
                                "breakdown": []}
                            with patch('Portfolio_info.portfolio_compute.compute_goal_insights') as mock_goals:
                                mock_goals.return_value = (None, None, [], None)
                                with patch('Portfolio_info.portfolio_compute.get_market_prices') as mock_prices:
                                    mock_prices.return_value = np.array([100.0] * 30)
                                    with patch('Portfolio_info.portfolio_compute.detect_market_regime') as mock_regime:
                                        mock_regime.return_value = {
                                            "regime": "bull",
                                            "score": 0.7}
                                        with patch('Portfolio_info.portfolio_compute.explain_portfolio_logic') as mock_explain:
                                            mock_explain.return_value = "Test explanation"
                                            with patch('Portfolio_info.portfolio_compute.get_portfolio_profile') as mock_profile:
                                                mock_profile.return_value = Mock(cash=1000.0)
                                                result = await compute_portfolio_metrics(data)
                                                assert result is not None
                                                assert "positions_data" in result
                                                assert "total_value" in result
                                                assert "risk" in result
                                                assert "sector_exposure" in result