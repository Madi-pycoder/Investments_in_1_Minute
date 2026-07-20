class InvestmentsException(Exception):
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details}

class DatabaseError(InvestmentsException):
    pass

class PortfolioError(InvestmentsException):
    pass

class PortfolioNotFoundError(PortfolioError):
    pass

class InsufficientFundsError(PortfolioError):
    pass

class PositionError(PortfolioError):
    pass

class PositionNotFoundError(PositionError):
    pass

class InsufficientPositionError(PositionError):
    pass

class MarketDataError(InvestmentsException):
    pass

class TickerNotFoundError(MarketDataError):
    pass

class MarketDataUnavailableError(MarketDataError):
    pass

class InvalidTickerError(MarketDataError):
    pass

class RiskCalculationError(InvestmentsException):
    pass

class InsufficientHistoryError(RiskCalculationError):
    pass

class VolatilityCalculationError(RiskCalculationError):
    pass

class ShariahError(InvestmentsException):
    pass

class ShariahDataError(ShariahError):
    pass

class GoalError(InvestmentsException):
    pass

class GoalNotFoundError(GoalError):
    pass

class InvalidGoalParametersError(GoalError):
    pass

class ValidationError(InvestmentsException):
    pass

class CacheError(InvestmentsException):
    pass

class ExternalAPIError(InvestmentsException):
    pass

class RateLimitError(ExternalAPIError):
    pass

class AuthenticationError(InvestmentsException):
    pass

class UserNotFoundError(AuthenticationError):
    pass

class ConfigurationError(InvestmentsException):
    pass

class RebalanceError(InvestmentsException):
    pass

class OptimizationError(RebalanceError):
    pass
