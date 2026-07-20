import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from MainMetricsComputingFeatures.shariah import (
    clean_number,
    build_ratio_check,
    calculate_data_freshness,
    get_denominator,
    check_business,
    calculate_purification,
    calculate_data_quality,
    calculate_score,
    calculate_confidence,
    shariah_screen,
    calculate_stock_trust,
    calculate_portfolio_purification,
    determine_status,
    calculate_shariah_status)


@pytest.mark.unit
@pytest.mark.shariah
class TestDataCleaning:
    def test_clean_number_valid(self):
        result = clean_number(100.5)
        assert result == 100.5
    
    def test_clean_number_none(self):
        result = clean_number(None)
        assert result is None
    
    def test_clean_number_nan(self):
        result = clean_number(float('nan'))
        assert result is None
    
    def test_clean_number_inf(self):
        result = clean_number(float('inf'))
        assert result is None
    
    def test_clean_number_negative_inf(self):
        result = clean_number(float('-inf'))
        assert result is None
    
    def test_clean_number_string(self):
        result = clean_number("100.5")
        assert result == 100.5
    
    def test_clean_number_invalid_string(self):
        result = clean_number("invalid")
        assert isinstance(result, dict)
        assert "error" in result


@pytest.mark.unit
@pytest.mark.shariah
class TestRatioChecks:
    def test_build_ratio_check_compliant(self):
        result = build_ratio_check(
            name="Test Ratio",
            numerator_value=25.0,
            denominator_value=100.0,
            numerator_field="test_numerator",
            denominator_field="test_denominator",
            limit=0.30,
            formula="test_numerator / test_denominator")
        assert result["status"] == "соответствует"
        assert result["value"] == 0.25
        assert "В пределах нормы" in result["message"]
    
    def test_build_ratio_check_borderline(self):
        result = build_ratio_check(
            name="Test Ratio",
            numerator_value=31.0,
            denominator_value=100.0,
            numerator_field="test_numerator",
            denominator_field="test_denominator",
            limit=0.30,
            formula="test_numerator / test_denominator")
        assert result["status"] == "на грани"
        assert "Близко к допустимому пределу" in result["message"]
    
    def test_build_ratio_check_non_compliant(self):
        result = build_ratio_check(
            name="Test Ratio",
            numerator_value=40.0,
            denominator_value=100.0,
            numerator_field="test_numerator",
            denominator_field="test_denominator",
            limit=0.30,
            formula="test_numerator / test_denominator")
        assert result["status"] == "не соответствует"
        assert "Превышает допустимый предел" in result["message"]
    
    def test_build_ratio_check_missing_numerator(self):
        result = build_ratio_check(
            name="Test Ratio",
            numerator_value=None,
            denominator_value=100.0,
            numerator_field="test_numerator",
            denominator_field="test_denominator",
            limit=0.30,
            formula="test_numerator / test_denominator")
        assert result["status"] == "нейтральный"
        assert result["value"] is None
        assert "Недостаточно данных" in result["message"]
        assert "test_numerator" in result["missing_fields"]
    
    def test_build_ratio_check_zero_denominator(self):
        result = build_ratio_check(
            name="Test Ratio",
            numerator_value=25.0,
            denominator_value=0.0,
            numerator_field="test_numerator",
            denominator_field="test_denominator",
            limit=0.30,
            formula="test_numerator / test_denominator")
        assert result["status"] == "нейтральный"
        assert result["value"] is None


@pytest.mark.unit
@pytest.mark.shariah
class TestDataFreshness:
    def test_calculate_data_freshness_fresh(self):
        stock = {
            "financials_updated_at": datetime.now(timezone.utc) - timedelta(days=30)}
        result = calculate_data_freshness(stock)
        assert result["status"] == "Актуальные данные"
        assert result["days_old"] == 30
    
    def test_calculate_data_freshness_aging(self):
        stock = {
            "financials_updated_at": datetime.now(timezone.utc) - timedelta(days=120)}
        result = calculate_data_freshness(stock)
        assert result["status"] == "Данные устаревают"
        assert result["days_old"] == 120
    
    def test_calculate_data_freshness_old(self):
        stock = {
            "financials_updated_at": datetime.now(timezone.utc) - timedelta(days=200)}
        result = calculate_data_freshness(stock)
        assert result["status"] == "Данные устарели"
        assert result["days_old"] == 200
    
    def test_calculate_data_freshness_missing(self):
        stock = {}
        result = calculate_data_freshness(stock)
        assert result["status"] == "Данные устарели"
        assert result["days_old"] is None


@pytest.mark.unit
@pytest.mark.shariah
class TestDenominatorSelection:
    def test_get_denominator_aaoifi(self):
        stock = {"market_cap": 1000000, "total_assets": 2000000}
        denominator, type_name = get_denominator(stock, "AAOIFI")
        assert denominator == 1000000
        assert type_name == "market_cap"
    
    def test_get_denominator_msci(self):
        stock = {"market_cap": 1000000, "total_assets": 2000000}
        denominator, type_name = get_denominator(stock, "MSCI")
        assert denominator == 2000000
        assert type_name == "total_assets"
    
    def test_get_denominator_unknown_standard(self):
        stock = {"market_cap": 1000000}
        denominator, type_name = get_denominator(stock, "UNKNOWN")
        assert denominator is None
        assert type_name == "unknown"


@pytest.mark.unit
@pytest.mark.shariah
class TestBusinessActivityCheck:
    def test_check_business_forbidden(self):
        result = check_business("Brewing", "Consumer Defensive")
        assert result["status"] == "не соответствует"
        assert "alcohol" in result["matched_keyword"]
        assert "Запрещённая сфера деятельности" in result["message"]
    
    def test_check_business_questionable(self):
        result = check_business("Asset Management", "Financial Services")
        assert result["status"] == "на грани"
        assert "financial services" in result["matched_keyword"]
        assert "Сомнительная сфера деятельности" in result["message"]
    
    def test_check_business_compliant(self):
        result = check_business("Software", "Technology")
        assert result["status"] == "соответствует"
        assert result["matched_keyword"] is None
        assert "соответствует Шариату" in result["message"]
    
    def test_check_business_case_insensitive(self):
        result = check_business("BREWING", "CONSUMER DEFENSIVE")
        assert result["status"] == "не соответствует"
    
    def test_check_business_none_values(self):
        result = check_business(None, None)
        assert result["status"] == "соответствует"


@pytest.mark.unit
@pytest.mark.shariah
class TestPurificationCalculation:
    def test_calculate_purification_with_dividends(self):
        result = calculate_purification(
            dividends=100.0,
            interest_ratio=0.05,
            position_value=None)
        assert result == 5.0
    
    def test_calculate_purification_with_yield(self):
        result = calculate_purification(
            dividends=0.02,
            interest_ratio=0.05,
            position_value=10000.0)
        assert result == 10.0
    
    def test_calculate_purification_no_interest(self):
        result = calculate_purification(
            dividends=100.0,
            interest_ratio=0.0,
            position_value=None)
        assert result == 0.0
    
    def test_calculate_purification_no_dividends(self):
        result = calculate_purification(
            dividends=0.0,
            interest_ratio=0.05,
            position_value=None)
        assert result == 0.0
    
    def test_calculate_purification_none_interest(self):
        result = calculate_purification(
            dividends=100.0,
            interest_ratio=None,
            position_value=None)
        assert result == 0.0


@pytest.mark.unit
@pytest.mark.shariah
class TestDataQuality:
    def test_calculate_data_quality_complete(self):
        stock = {
            "market_cap": 1000000,
            "revenue": 500000,
            "total_debt": 200000,
            "total_cash": 100000,
            "receivables": 50000}
        quality = calculate_data_quality(stock)
        assert quality == 1.0
    
    def test_calculate_data_quality_partial(self):
        stock = {
            "market_cap": 1000000,
            "revenue": 500000,
            "total_debt": None,
            "total_cash": 100000,
            "receivables": None}
        quality = calculate_data_quality(stock)
        assert 0 < quality < 1.0
    
    def test_calculate_data_quality_minimal(self):
        stock = {"market_cap": 1000000}
        quality = calculate_data_quality(stock)
        assert quality < 0.5


@pytest.mark.unit
@pytest.mark.shariah
class TestScoreCalculation:
    def test_calculate_score_all_compliant(self):
        results = {
            "market_cap": "соответствует",
            "revenue": "соответствует",
            "total_debt": "соответствует",
            "total_cash": "соответствует",
            "receivables": "соответствует",
            "interest_income": "соответствует"}
        score = calculate_score(results)
        assert score == 100
    
    def test_calculate_score_mixed(self):
        results = {
            "market_cap": "соответствует",
            "revenue": "соответствует",
            "total_debt": "на грани",
            "total_cash": "соответствует",
            "receivables": "не соответствует",
            "interest_income": "нейтральный"}
        score = calculate_score(results)
        assert 50 < score < 100
    
    def test_calculate_score_all_non_compliant(self):
        results = {
            "market_cap": "не соответствует",
            "revenue": "не соответствует",
            "total_debt": "не соответствует",
            "total_cash": "не соответствует",
            "receivables": "не соответствует",
            "interest_income": "не соответствует"}
        score = calculate_score(results)
        assert score < 50


@pytest.mark.unit
@pytest.mark.shariah
class TestConfidenceCalculation:
    def test_calculate_confidence_high(self):
        confidence = calculate_confidence(data_quality=0.95, borderline_count=0)
        assert confidence == 95.0
    
    def test_calculate_confidence_with_borderline(self):
        confidence = calculate_confidence(data_quality=0.90, borderline_count=2)
        assert confidence < 90.0
    
    def test_calculate_confidence_low_quality(self):
        confidence = calculate_confidence(data_quality=0.50, borderline_count=1)
        assert confidence < 50.0
    
    def test_calculate_confidence_minimum(self):
        confidence = calculate_confidence(data_quality=0.0, borderline_count=10)
        assert confidence == 0.0


@pytest.mark.unit
@pytest.mark.shariah
class TestShariahScreening:
    @pytest.mark.asyncio
    async def test_shariah_screen_compliant(self, sample_stock_data):
        result = await shariah_screen(sample_stock_data)
        assert result is not None
        assert "status" in result
        assert "audit" in result
        assert "confidence" in result
    
    @pytest.mark.asyncio
    async def test_shariah_screen_forced_haram(self):
        stock = {
            "ticker": "SPY",
            "industry": "Finance",
            "sector": "Financial Services"}
        result = await shariah_screen(stock)
        assert result["status"] == "НЕ СООТВЕТСТВУЕТ ❌"
        assert result["confidence"] == 100
    
    @pytest.mark.asyncio
    async def test_shariah_screen_forbidden_business(self):
        stock = {
            "ticker": "BREW",
            "industry": "Brewing",
            "sector": "Consumer Defensive",
            "market_cap": 1000000,
            "total_debt": 200000,
            "total_cash": 100000,
            "total_assets": 500000,
            "receivables": 50000,
            "revenue": 300000,
            "interest_income": 10000,
            "financials_updated_at": datetime.now(timezone.utc)}
        result = await shariah_screen(stock)
        assert result["status"] == "НЕ СООТВЕТСТВУЕТ ❌"
    
    @pytest.mark.asyncio
    async def test_shariah_screen_msci_standard(self, sample_stock_data):
        result = await shariah_screen(sample_stock_data, standard="MSCI")
        assert result is not None
        assert result["audit"]["standard"] == "MSCI"


@pytest.mark.unit
@pytest.mark.shariah
class TestStockTrust:
    def test_calculate_stock_trust_compliant(self):
        screening = {
            "status": "СООТВЕТСТВУЕТ ШАРИАТУ ✅",
            "audit": {
                "freshness": {"status": "Актуальные данные"},
                "missing_fields": []},
            "confidence": 90}
        trust = calculate_stock_trust(screening)
        assert trust > 0.8
    
    def test_calculate_stock_trust_old_data(self):
        screening = {
            "status": "СООТВЕТСТВУЕТ ШАРИАТУ ✅",
            "audit": {
                "freshness": {"status": "Данные устарели"},
                "missing_fields": []},
            "confidence": 90}
        trust = calculate_stock_trust(screening)
        assert trust < 0.9
    
    def test_calculate_stock_trust_missing_fields(self):
        screening = {
            "status": "СООТВЕТСТВУЕТ ШАРИАТУ ✅",
            "audit": {
                "freshness": {"status": "Актуальные данные"},
                "missing_fields": ["field1", "field2"]},
            "confidence": 90}
        trust = calculate_stock_trust(screening)
        assert trust < 0.9
    
    def test_calculate_stock_trust_non_compliant(self):
        screening = {
            "status": "НЕ СООТВЕТСТВУЕТ ❌",
            "audit": {
                "freshness": {"status": "Актуальные данные"},
                "missing_fields": []},
            "confidence": 90}
        trust = calculate_stock_trust(screening)
        assert trust < 0.5


@pytest.mark.unit
@pytest.mark.shariah
class TestPortfolioPurification:
    @pytest.mark.asyncio
    async def test_calculate_portfolio_purification(self, sample_positions):
        stocks_data = {
            "AAPL": {
                "ticker": "AAPL",
                "dividends": 0.5,
                "interest_income": 10000},
            "MSFT": {
                "ticker": "MSFT",
                "dividends": 0.8,
                "interest_income": 15000}}
        with patch('MainMetricsComputingFeatures.shariah.shariah_screen') as mock_screen:
            mock_screen.return_value = {
                "audit": {"checks": [
                    {"name": "Доход от процентов", "value": 0.05}]}}
            result = await calculate_portfolio_purification(sample_positions, stocks_data)
            assert result is not None
            assert "total_purification" in result
            assert "breakdown" in result
    
    @pytest.mark.asyncio
    async def test_calculate_portfolio_purification_empty(self):
        result = await calculate_portfolio_purification([], {})
        assert result["total_purification"] == 0
        assert result["breakdown"] == []


@pytest.mark.unit
@pytest.mark.shariah
class TestStatusDetermination:
    def test_determine_status_compliant(self):
        results = {"business": "соответствует"}
        score = 85
        status = determine_status(results, score)
        assert status == "СООТВЕТСТВУЕТ ШАРИАТУ ✅"
    
    def test_determine_status_non_compliant_business(self):
        results = {"business": "не соответствует"}
        score = 50
        status = determine_status(results, score)
        assert status == "НЕ СООТВЕТСТВУЕТ ❌"
    
    def test_determine_status_likely_compliant(self):
        results = {"business": "соответствует"}
        score = 65
        status = determine_status(results, score)
        assert "Скорее соответствует" in status
    
    def test_determine_status_needs_review(self):
        results = {"business": "соответствует"}
        score = 55
        status = determine_status(results, score)
        assert "Нужна дополнительная проверка" in status
    
    def test_calculate_shariah_status_compliant(self):
        positions_data = [
            {"ticker": "AAPL", "shariah_compliant": True},
            {"ticker": "MSFT", "shariah_compliant": True}]
        status = calculate_shariah_status(positions_data)
        assert "соответствует Шариату" in status
    
    def test_calculate_shariah_status_one_haram(self):
        positions_data = [
            {"ticker": "AAPL", "shariah_compliant": True},
            {"ticker": "SPY", "shariah_compliant": False}]
        status = calculate_shariah_status(positions_data)
        assert "спорные активы" in status
        assert "SPY" in status
    
    def test_calculate_shariah_status_multiple_haram(self):
        positions_data = [
            {"ticker": "AAPL", "shariah_compliant": True},
            {"ticker": "SPY", "shariah_compliant": False},
            {"ticker": "VOO", "shariah_compliant": False}]
        status = calculate_shariah_status(positions_data)
        assert "спорные активы" in status
        assert "2" in status
    
    def test_calculate_shariah_status_empty(self):
        status = calculate_shariah_status([])
        assert "соответствует Шариату" in status