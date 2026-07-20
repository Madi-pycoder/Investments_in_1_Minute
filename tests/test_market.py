import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from MarketFeatures.market import (
    clean_number,
    safe_close,
    last_valid_close,
    get_price_fallback,
    get_index_proxy,
    get_fx_rate,
    get_stocks_batch,
    detect_etf_type,
    validate_and_normalize,
    load_yahoo_full_holdings,
    load_universal_fallback,
    normalize_holdings,
    get_etf_holdings,
    get_prices_only)


@pytest.mark.unit
@pytest.mark.market
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
    
    def test_clean_number_string(self):
        result = clean_number("100.5")
        assert result == 100.5


@pytest.mark.unit
@pytest.mark.market
class TestPriceUtilities:
    def test_safe_close_with_data(self):
        df = pd.DataFrame({"Close": [100.0, 101.0, 102.0]})
        result = safe_close(df)
        assert result == 102.0
    
    def test_safe_close_empty(self):
        df = pd.DataFrame()
        result = safe_close(df)
        assert result is None
    
    def test_safe_close_none(self):
        result = safe_close(None)
        assert result is None
    
    def test_last_valid_close_with_data(self):
        df = pd.DataFrame({"Close": [100.0, 101.0, 102.0]})
        result = last_valid_close(df)
        assert result == 102.0
    
    def test_last_valid_close_with_nans(self):
        df = pd.DataFrame({"Close": [100.0, np.nan, 102.0]})
        result = last_valid_close(df)
        assert result == 102.0
    
    def test_last_valid_close_all_nans(self):
        df = pd.DataFrame({"Close": [np.nan, np.nan, np.nan]})
        result = last_valid_close(df)
        assert result is None


@pytest.mark.unit
@pytest.mark.market
class TestPriceFallback:
    @patch('MarketFeatures.market.requests.get')
    def test_get_price_fallback_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chart": {"result": [{
                "meta": {"regularMarketPrice": 150.0}}]}}
        mock_get.return_value = mock_response
        result = get_price_fallback("AAPL")
        assert result == 150.0
    
    @patch('MarketFeatures.market.requests.get')
    def test_get_price_fallback_no_result(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"chart": {"result": None}}
        mock_get.return_value = mock_response
        result = get_price_fallback("AAPL")
        assert result is None
    
    @patch('MarketFeatures.market.requests.get')
    def test_get_price_fallback_error(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        result = get_price_fallback("AAPL")
        assert result is None


@pytest.mark.unit
@pytest.mark.market
class TestIndexProxy:
    @pytest.mark.asyncio
    async def test_get_index_proxy_spy(self):
        result = await get_index_proxy("SPY")
        assert result is not None
        assert isinstance(result, list)
        assert "AAPL" in result
    
    @pytest.mark.asyncio
    async def test_get_index_proxy_qqq(self):
        result = await get_index_proxy("QQQ")
        assert result is not None
        assert isinstance(result, list)
        assert "NVDA" in result
    
    @pytest.mark.asyncio
    async def test_get_index_proxy_unknown(self):
        with patch('MarketFeatures.market.detect_etf_type') as mock_type:
            mock_type.return_value = None
            result = await get_index_proxy("UNKNOWN")
            assert result is not None
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.market
class TestFXRate:
    @pytest.mark.asyncio
    async def test_get_fx_rate_same_currency(self):
        result = await get_fx_rate("USD", "USD")
        assert result == 1.0
    
    @pytest.mark.asyncio
    async def test_get_fx_rate_none_currency(self):
        result = await get_fx_rate(None, "USD")
        assert result == 1.0


@pytest.mark.unit
@pytest.mark.market
class TestHoldingsValidation:
    def test_validate_and_normalize_valid(self):
        holdings = [
            {"ticker": "AAPL", "weight": 0.5},
            {"ticker": "MSFT", "weight": 0.5}]
        result = validate_and_normalize(holdings)
        assert result is not None
        assert len(result) == 2
        assert sum(h["weight"] for h in result) == 1.0

    def test_validate_and_normalize_unnormalized(self):
        holdings = [
            {"ticker": "AAPL", "weight": 0.3},
            {"ticker": "MSFT", "weight": 0.3}]
        result = validate_and_normalize(holdings)
        assert result is not None
        assert sum(h["weight"] for h in result) == 1.0
    
    def test_validate_and_normalize_zero_total(self):
        holdings = [
            {"ticker": "AAPL", "weight": 0.0},
            {"ticker": "MSFT", "weight": 0.0}]
        result = validate_and_normalize(holdings)
        assert result is None
    
    def test_validate_and_normalize_empty(self):
        result = validate_and_normalize([])
        assert result is None
    
    def test_validate_and_normalize_missing_ticker(self):
        holdings = [
            {"weight": 0.5},
            {"ticker": "MSFT", "weight": 0.5}]
        result = validate_and_normalize(holdings)
        assert len(result) == 1
    
    def test_normalize_holdings(self):
        holdings = [
            {"ticker": "AAPL", "weight": 0.3},
            {"ticker": "MSFT", "weight": 0.3}]
        result = normalize_holdings(holdings)
        assert sum(h["weight"] for h in result) == 1.0
        assert result[0]["weight"] == 0.5
        assert result[1]["weight"] == 0.5


@pytest.mark.unit
@pytest.mark.market
class TestETFTypeDetection:
    @pytest.mark.asyncio
    async def test_detect_etf_type_vanguard(self):
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.get_modules.return_value = {
                "TEST": {"fundProfile": {"family": "Vanguard"}}}
            mock_ticker.return_value = mock_instance
            result = await detect_etf_type("TEST")
            assert result == "vanguard"
    
    @pytest.mark.asyncio
    async def test_detect_etf_type_blackrock(self):
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.get_modules.return_value = {
                "TEST": {"fundProfile": {"family": "iShares"}}}
            mock_ticker.return_value = mock_instance
            result = await detect_etf_type("TEST")
            assert result == "blackrock"
    
    @pytest.mark.asyncio
    async def test_detect_etf_type_shariah(self):
        """Test detection of Shariah ETF."""
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.get_modules.return_value = {
                "TEST": {"fundProfile": {"family": "Wahed", "categoryName": "Shariah"}}}
            mock_ticker.return_value = mock_instance
            result = await detect_etf_type("TEST")
            assert result == "shariah"
    
    @pytest.mark.asyncio
    async def test_detect_etf_type_generic(self):
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.get_modules.return_value = {
                "TEST": {"fundProfile": {"family": "Generic Fund"}}}
            mock_ticker.return_value = mock_instance
            result = await detect_etf_type("TEST")
            assert result == "generic"
    
    @pytest.mark.asyncio
    async def test_detect_etf_type_error(self):
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("Error")
            result = await detect_etf_type("TEST")
            assert result is None


@pytest.mark.unit
@pytest.mark.market
class TestHoldingsLoading:
    @pytest.mark.asyncio
    async def test_load_yahoo_full_holdings_success(self):
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.get_modules.return_value = {
                "TEST": {"holdings": [{"symbol": "AAPL", "holdingPercent": 0.15},
                    {"symbol": "MSFT", "holdingPercent": 0.10}]}}
            mock_ticker.return_value = mock_instance
            result = await load_yahoo_full_holdings("TEST")
            assert result is not None
            assert len(result) == 2
            assert result[0]["ticker"] == "AAPL"
            assert result[0]["weight"] == 0.15
    
    @pytest.mark.asyncio
    async def test_load_yahoo_full_holdings_empty(self):
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.get_modules.return_value = {
                "TEST": {"holdings": []}}
            mock_ticker.return_value = mock_instance
            result = await load_yahoo_full_holdings("TEST")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_load_yahoo_full_holdings_no_holdings(self):
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.get_modules.return_value = {"TEST": {}}
            mock_ticker.return_value = mock_instance
            result = await load_yahoo_full_holdings("TEST")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_load_universal_fallback_success(self):
        with patch('MarketFeatures.market.Ticker') as mock_ticker:
            mock_instance = Mock()
            mock_instance.get_modules.return_value = {
                "TEST": {"holdings": [{"symbol": "AAPL"},
                    {"symbol": "MSFT"}]}}
            mock_ticker.return_value = mock_instance
            result = await load_universal_fallback("TEST")
            assert result is not None
            assert len(result) == 2
            assert result[0]["weight"] == 0.5


@pytest.mark.unit
@pytest.mark.market
class TestBatchOperations:
    @pytest.mark.asyncio
    async def test_get_stocks_batch(self):
        with patch('MarketFeatures.market.fetch_chunk_limited') as mock_fetch:
            mock_fetch.return_value = {
                "AAPL": {
                    "sector": "Technology",
                    "industry": "Consumer Electronics"},
                "MSFT": {
                    "sector": "Technology",
                    "industry": "Software"}}
            result = await get_stocks_batch(["AAPL", "MSFT"])
            assert result is not None
            assert "AAPL" in result
            assert "MSFT" in result
    
    @pytest.mark.asyncio
    async def test_get_stocks_batch_with_cache(self):
        from MarketFeatures.market import STOCKS_CACHE
        STOCKS_CACHE["AAPL"] = {"sector": "Technology"}
        with patch('MarketFeatures.market.fetch_chunk_limited') as mock_fetch:
            mock_fetch.return_value = {"MSFT": {"sector": "Technology"}}
            result = await get_stocks_batch(["AAPL", "MSFT"])
            assert "AAPL" in result
            assert "MSFT" in result


@pytest.mark.unit
@pytest.mark.market
class TestGetPricesOnly:
    @pytest.mark.asyncio
    async def test_get_prices_only_success(self):
        """Test successful price retrieval for multiple tickers."""
        with patch('MarketFeatures.market.yf.download') as mock_download:
            mock_df = pd.DataFrame({
                "Close": {"AAPL": 150.0, "MSFT": 300.0, "GOOGL": 120.0}})
            mock_download.return_value = mock_df
            result = await get_prices_only(["AAPL", "MSFT", "GOOGL"])
            assert result is not None
            assert "AAPL" in result
            assert "MSFT" in result
            assert "GOOGL" in result
    
    @pytest.mark.asyncio
    async def test_get_prices_only_with_error(self):
        with patch('MarketFeatures.market.yf.download') as mock_download:
            mock_download.side_effect = Exception("Network error")
            result = await get_prices_only(["AAPL", "MSFT"])
            assert isinstance(result, dict)


@pytest.mark.unit
@pytest.mark.market
class TestGetETFHoldings:
    @pytest.mark.asyncio
    async def test_get_etf_holdings_yahoo_success(self):
        with patch('MarketFeatures.market.load_yahoo_full_holdings') as mock_yahoo:
            mock_yahoo.return_value = [
                {"ticker": "AAPL", "weight": 0.15},
                {"ticker": "MSFT", "weight": 0.12},
                {"ticker": "GOOGL", "weight": 0.10}]
            result = await get_etf_holdings("TEST")
            assert result is not None
            assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_get_etf_holdings_low_coverage(self):
        with patch('MarketFeatures.market.load_yahoo_full_holdings') as mock_yahoo:
            mock_yahoo.return_value = [{"ticker": "AAPL", "weight": 0.15}]
            with patch('MarketFeatures.market.get_index_proxy') as mock_proxy:
                mock_proxy.return_value = ["AAPL", "MSFT", "GOOGL"]
                result = await get_etf_holdings("TEST")
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_etf_holdings_yahoo_failed(self):
        with patch('MarketFeatures.market.load_yahoo_full_holdings') as mock_yahoo:
            mock_yahoo.return_value = None
            with patch('MarketFeatures.market.get_index_proxy') as mock_proxy:
                mock_proxy.return_value = ["AAPL", "MSFT", "GOOGL"]
                result = await get_etf_holdings("TEST")
                assert result is not None
                assert len(result) == 3