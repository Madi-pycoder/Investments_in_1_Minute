# Testing Guide

This document provides comprehensive information about the test suite for the Investments in 1 Minute project.

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures and utilities
├── test_smoke.py                    # Basic smoke test
├── test_riskmanagement.py           # Risk management unit tests
├── test_shariah.py                  # Shariah compliance unit tests
├── test_market.py                   # Market data unit tests
├── test_portfolio_compute.py        # Portfolio computation unit tests
├── test_backend.py                  # Database backend unit tests
├── test_integration_database.py     # Database integration tests
└── test_integration_portfolio.py    # Portfolio workflow integration tests
```

## Test Categories

### Unit Tests
- **test_riskmanagement.py**: Tests for risk calculations, volatility, beta, Sharpe ratio, and portfolio risk metrics
- **test_shariah.py**: Tests for Shariah compliance screening, business activity checks, and purification calculations
- **test_market.py**: Tests for market data retrieval, price fetching, ETF holdings, and FX rates
- **test_portfolio_compute.py**: Tests for portfolio metrics, position data, sector exposure, and rebalancing
- **test_backend.py**: Tests for database operations, user management, and transaction handling

### Integration Tests
- **test_integration_database.py**: End-to-end database workflows including user creation, portfolio management, and cascade deletions
- **test_integration_portfolio.py**: Complete portfolio workflows including risk analysis, Shariah screening, and rebalancing

## Running Tests

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_riskmanagement.py
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Run Only Unit Tests
```bash
pytest -m unit
```

### Run Only Integration Tests
```bash
pytest -m integration
```

### Run Specific Markers
```bash
pytest -m risk          # Risk calculation tests
pytest -m shariah       # Shariah compliance tests
pytest -m market        # Market data tests
pytest -m portfolio     # Portfolio management tests
pytest -m database      # Database tests
```

### Run with Verbose Output
```bash
pytest -v
```

### Run with Parallel Execution
```bash
pytest -n auto
```

## Test Fixtures

The `conftest.py` file provides shared fixtures:

- `db_session`: Async database session for testing
- `sample_stock_data`: Sample stock data for testing
- `sample_positions`: Sample portfolio positions
- `sample_price_history`: Sample price history data
- `sample_goals`: Sample financial goals
- `mock_yf_ticker`: Mock yfinance Ticker object
- `mock_cache`: Mock cache object

## Coverage Goals

The test suite is designed to achieve **60-70% code coverage** across the following modules:

- MainMetricsComputingFeatures (riskmanagement, shariah)
- MarketFeatures (market, market_regime)
- Portfolio_info (portfolio_compute)
- Portfolio_Handlers (portfolio handlers)
- MainEngines (engines)
- ProjectDataBase (backend, models, cache)

## Coverage Report

After running tests with coverage, view the HTML report:

```bash
open htmlcov/index.html
```

## Test Markers

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow running tests
- `@pytest.mark.market`: Market data tests
- `@pytest.mark.database`: Database tests
- `@pytest.mark.shariah`: Shariah compliance tests
- `@pytest.mark.risk`: Risk calculation tests
- `@pytest.mark.portfolio`: Portfolio management tests

## Writing New Tests

1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test complete workflows and interactions between components
3. **Use Fixtures**: Leverage existing fixtures from `conftest.py`
4. **Mock External Dependencies**: Use `unittest.mock` for external APIs
5. **Async Tests**: Use `@pytest.mark.asyncio` for async functions

### Example Unit Test

```python
import pytest
from unittest.mock import patch

@pytest.mark.unit
@pytest.mark.risk
class TestRiskCalculations:
    
    @pytest.mark.asyncio
    async def test_calculate_volatility(self):
        with patch('module.get_history_df') as mock_hist:
            mock_hist.return_value = sample_data
            result = await calculate_volatility("AAPL")
            assert result is not None
```

### Example Integration Test

```python
@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, db_session):
        # Create user
        await set_user(12345)
        
        # Create portfolio
        portfolio_id = await create_demo_portfolio(12345, "Test")
        
        # Verify
        portfolio = await get_portfolio(portfolio_id)
        assert portfolio is not None
```

## Troubleshooting

### Database Tests Fail
Ensure SQLite is available and the test database can be created in memory.

### Async Tests Fail
Make sure `pytest-asyncio` is installed and configured properly in `pytest.ini`.

### Import Errors
Ensure the project root is in the Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Coverage Not Generated
Install `pytest-cov` and ensure the `.coveragerc` file is properly configured.

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: pytest --cov=. --cov-report=xml
  
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Best Practices

1. **Keep Tests Independent**: Each test should run independently
2. **Use Descriptive Names**: Test names should clearly describe what they test
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
4. **Mock External Services**: Don't rely on external APIs in tests
5. **Clean Up Resources**: Use fixtures with proper cleanup
6. **Test Edge Cases**: Include tests for boundary conditions and error cases
7. **Maintain Test Speed**: Keep tests fast by using mocks and avoiding slow operations

## Contributing

When adding new features:

1. Write unit tests for new functions
2. Add integration tests for new workflows
3. Ensure coverage remains above 60%
4. Update this README if adding new test files
5. Run the full test suite before committing

## Test Statistics

- **Total Test Files**: 8
- **Unit Test Files**: 5
- **Integration Test Files**: 2
- **Estimated Test Count**: 200+
- **Target Coverage**: 60-70%
- **Test Execution Time**: ~2-5 minutes (depending on environment)
