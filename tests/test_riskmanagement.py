import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from unittest.mock import patch
from MainMetricsComputingFeatures.riskmanagement import (
    calculate_volatility,
    calculate_max_drawdown,
    calculate_beta,
    calculate_sharpe_ratio,
    calculate_risk_score,
    get_risk_label,
    calculate_diversification_score,
    calculate_concentration_risk,
    calculate_portfolio_risk,
    calculate_portfolio_risk_score,
    generate_risk_alerts,
    calculate_optimal_weights,
    stress_test_portfolio,
    ensure_series,
    make_portfolio_cache_key)


@pytest.mark.unit
@pytest.mark.risk
class TestRiskCalculations:
    @pytest.mark.asyncio
    async def test_calculate_volatility_with_valid_data(self, sample_price_history):
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_hist.return_value = sample_price_history
            result = await calculate_volatility("AAPL")
            assert result is not None
            assert result >= 0
            assert result <= 100

    @pytest.mark.asyncio
    async def test_calculate_volatility_with_insufficient_data(self):
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            short_df = pd.DataFrame({"Close": [100.0]})
            mock_hist.return_value = short_df
            result = await calculate_volatility("AAPL")
            assert result is None

    @pytest.mark.asyncio
    async def test_calculate_volatility_with_no_data(self):
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_hist.return_value = None
            result = await calculate_volatility("AAPL")
            assert result is None

    @pytest.mark.asyncio
    async def test_calculate_max_drawdown(self, sample_price_history):
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_hist.return_value = sample_price_history
            result = await calculate_max_drawdown("AAPL")
            assert result is not None
            assert result <= 0
            assert result >= -100

    @pytest.mark.asyncio
    async def test_calculate_beta(self, sample_price_history):
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_hist.side_effect = [sample_price_history, sample_price_history]
            result = await calculate_beta("AAPL")
            assert result is not None
            assert isinstance(result, float)

    @pytest.mark.asyncio
    async def test_calculate_beta_with_no_market_data(self, sample_price_history):
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_hist.side_effect = [sample_price_history, None]
            result = await calculate_beta("AAPL")
            assert result is None

    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio(self, sample_price_history):
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_hist.return_value = sample_price_history
            result = await calculate_sharpe_ratio("AAPL")
            assert result is not None
            assert isinstance(result, float)

    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio_with_zero_std(self):
        constant_df = pd.DataFrame({"Close": [100.0] * 50})
        with patch('MainMetricsComputingFeatures.riskmanagement.get_history_df') as mock_hist:
            mock_hist.return_value = constant_df
            result = await calculate_sharpe_ratio("AAPL")
            assert result is None


@pytest.mark.unit
@pytest.mark.risk
class TestRiskScoring:
    def test_calculate_risk_score_high_risk(self):
        score = calculate_risk_score(
            volatility=50.0,
            drawdown=-70.0,
            beta=2.0,
            sharpe=0.3)
        assert score is not None
        assert score < 50

    def test_calculate_risk_score_low_risk(self):
        score = calculate_risk_score(
            volatility=10.0,
            drawdown=-10.0,
            beta=0.8,
            sharpe=2.5)
        assert score is not None
        assert score > 80

    def test_calculate_risk_score_with_missing_data(self):
        score = calculate_risk_score(
            volatility=20.0,
            drawdown=None,
            beta=1.0,
            sharpe=None)
        assert score is not None

    def test_calculate_risk_score_insufficient_data(self):
        score = calculate_risk_score(
            volatility=None,
            drawdown=None,
            beta=None,
            sharpe=1.0)
        assert score is None

    def test_get_risk_label_low(self):
        label = get_risk_label(85)
        assert label == "Низкий Риск 🟢"

    def test_get_risk_label_medium(self):
        label = get_risk_label(65)
        assert label == "Средний Риск 🟡"

    def test_get_risk_label_high(self):
        label = get_risk_label(50)
        assert label == "Высокий Риск 🟠"

    def test_get_risk_label_very_high(self):
        label = get_risk_label(30)
        assert label == "Очень Высокий Риск 🔴"

    def test_get_risk_label_none(self):
        label = get_risk_label(None)
        assert label == "Unknown"


@pytest.mark.unit
@pytest.mark.risk
class TestPortfolioRisk:
    def test_ensure_series_with_dataframe(self):
        df = pd.DataFrame({"Close": [1, 2, 3]})
        result = ensure_series(df)
        assert isinstance(result, pd.Series)

    def test_ensure_series_with_series(self):
        series = pd.Series([1, 2, 3])
        result = ensure_series(series)
        assert isinstance(result, pd.Series)

    def test_make_portfolio_cache_key(self):
        positions = [
            {"ticker": "AAPL", "weight": 0.5},
            {"ticker": "MSFT", "weight": 0.5}]
        key = make_portfolio_cache_key(positions)
        assert isinstance(key, tuple)
        assert len(key) == 2

    def test_calculate_diversification_score(self):
        positions = [
            {"ticker": "AAPL", "weight": 0.25},
            {"ticker": "MSFT", "weight": 0.25},
            {"ticker": "GOOGL", "weight": 0.25},
            {"ticker": "AMZN", "weight": 0.25}]
        score = calculate_diversification_score(positions)
        assert score is not None
        assert score > 0
        assert score <= 100

    def test_calculate_diversification_score_concentrated(self):
        positions = [
            {"ticker": "AAPL", "weight": 0.8},
            {"ticker": "MSFT", "weight": 0.2}]
        score = calculate_diversification_score(positions)
        assert score is not None
        assert score < 50

    def test_calculate_diversification_score_empty(self):
        score = calculate_diversification_score([])
        assert score is None

    def test_calculate_concentration_risk_high(self):
        positions = [
            {"ticker": "AAPL", "weight": 0.6},
            {"ticker": "MSFT", "weight": 0.4}]
        risk = calculate_concentration_risk(positions)
        assert "🔴" in risk

    def test_calculate_concentration_risk_moderate(self):
        positions = [
            {"ticker": "AAPL", "weight": 0.4},
            {"ticker": "MSFT", "weight": 0.3},
            {"ticker": "GOOGL", "weight": 0.3}]
        risk = calculate_concentration_risk(positions)
        assert "🟡" in risk or "🟠" in risk

    def test_calculate_concentration_risk_good(self):
        positions = [
            {"ticker": "AAPL", "weight": 0.2},
            {"ticker": "MSFT", "weight": 0.2},
            {"ticker": "GOOGL", "weight": 0.2},
            {"ticker": "AMZN", "weight": 0.2},
            {"ticker": "NVDA", "weight": 0.2}]
        risk = calculate_concentration_risk(positions)
        assert "🟢" in risk

    def test_calculate_concentration_risk_empty(self):
        risk = calculate_concentration_risk([])
        assert risk is None

    def test_calculate_portfolio_risk_score(self):
        score = calculate_portfolio_risk_score(
            volatility=20.0,
            diversification=75.0)
        assert score is not None
        assert 0 <= score <= 100

    def test_calculate_portfolio_risk_score_high_volatility(self):
        score = calculate_portfolio_risk_score(
            volatility=40.0,
            diversification=80.0)
        assert score is not None
        assert score < 70

    def test_calculate_portfolio_risk_score_low_diversification(self):
        score = calculate_portfolio_risk_score(
            volatility=15.0,
            diversification=30.0)
        assert score is not None
        assert score < 85

    def test_calculate_portfolio_risk_score_missing_data(self):
        score = calculate_portfolio_risk_score(
            volatility=None,
            diversification=75.0)
        assert score is None

    @pytest.mark.asyncio
    async def test_calculate_portfolio_risk(self, sample_positions):
        with patch('MainMetricsComputingFeatures.riskmanagement.calculate_portfolio_volatility') as mock_vol:
            mock_vol.return_value = 20.0
            result = await calculate_portfolio_risk(sample_positions)
            assert result is not None
            assert "volatility" in result
            assert "diversification" in result
            assert "concentration" in result
            assert "risk_score" in result

    @pytest.mark.asyncio
    async def test_calculate_portfolio_risk_empty(self):
        result = await calculate_portfolio_risk([])
        assert result is None


@pytest.mark.unit
@pytest.mark.risk
class TestRiskAlerts:
    def test_generate_risk_alerts_high_volatility(self):
        risk = {
            "volatility": 35.0,
            "diversification": 70.0,
            "concentration": "Хорошая Диверсификация 🟢"}
        alerts = generate_risk_alerts(risk)
        assert len(alerts) > 0
        assert any("колеблется" in alert for alert in alerts)

    def test_generate_risk_alerts_low_diversification(self):
        risk = {
            "volatility": 20.0,
            "diversification": 30.0,
            "concentration": "Хорошая Диверсификация 🟢"}
        alerts = generate_risk_alerts(risk)
        assert len(alerts) > 0
        assert any("диверсифицированы" in alert for alert in alerts)

    def test_generate_risk_alerts_high_concentration(self):
        risk = {
            "volatility": 20.0,
            "diversification": 70.0,
            "concentration": "Слишком Крупная Доля 🔴"}
        alerts = generate_risk_alerts(risk)
        assert len(alerts) > 0
        assert any("доля" in alert for alert in alerts)

    def test_generate_risk_alerts_no_risks(self):
        risk = {
            "volatility": 15.0,
            "diversification": 80.0,
            "concentration": "Хорошая Диверсификация 🟢"}
        alerts = generate_risk_alerts(risk)
        assert len(alerts) == 0

    def test_generate_risk_alerts_none(self):
        alerts = generate_risk_alerts(None)
        assert alerts == []


@pytest.mark.unit
@pytest.mark.risk
class TestStressTesting:
    def test_stress_test_portfolio(self, sample_positions):
        results = stress_test_portfolio(sample_positions)
        assert results is not None
        assert isinstance(results, dict)
        assert len(results) > 0
        expected_scenarios = [
            "Кризис 2008 года",
            "Крах доткомов",
            "Падние рынка во время COVID-19",
            "Шокирующая инфляция",
            "Небольшая коррекция рынка"]
        for scenario in expected_scenarios:
            assert scenario in results
            assert isinstance(results[scenario], (int, float))

    def test_stress_test_portfolio_empty(self):
        results = stress_test_portfolio([])
        assert results is None

    def test_stress_test_portfolio_values(self, sample_positions):
        results = stress_test_portfolio(sample_positions)

        for scenario, loss in results.items():
            assert loss <= 0
            assert loss >= -100


@pytest.mark.unit
@pytest.mark.risk
class TestOptimization:
    @pytest.mark.asyncio
    async def test_calculate_optimal_weights(self, sample_positions):
        with patch('MainMetricsComputingFeatures.riskmanagement.build_returns_dataframe') as mock_df:
            dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='D')
            mock_returns = pd.DataFrame({
                "AAPL": np.random.normal(0.001, 0.02, 100),
                "MSFT": np.random.normal(0.001, 0.02, 100),
                "GOOGL": np.random.normal(0.001, 0.02, 100),
                "AMZN": np.random.normal(0.001, 0.02, 100),
                "NVDA": np.random.normal(0.001, 0.02, 100)}, index=dates)
            mock_df.return_value = mock_returns
            result = await calculate_optimal_weights(sample_positions)
            assert result is not None
            assert isinstance(result, dict)
            total_weight = sum(result.values())
            assert 0.95 <= total_weight <= 1.05

    @pytest.mark.asyncio
    async def test_calculate_optimal_weights_empty(self):
        result = await calculate_optimal_weights([])
        assert result is None

    @pytest.mark.asyncio
    async def test_calculate_optimal_weights_no_returns(self, sample_positions):
        with patch('MainMetricsComputingFeatures.riskmanagement.build_returns_dataframe') as mock_df:
            mock_df.return_value = None
            result = await calculate_optimal_weights(sample_positions)
            assert result is None