from datetime import datetime, date
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, confloat
from enum import Enum


class InvestmentStyle(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"

class RiskTolerance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ShariahStandard(str, Enum):
    AAOIFI = "AAOIFI"
    MSCI = "MSCI"

class ComplianceStatus(str, Enum):
    COMPLIANT = "СООТВЕТСТВУЕТ ШАРИАТУ ✅"
    LIKELY_COMPLIANT = "Скорее соответствует Шариату ⚠️"
    NEEDS_REVIEW = "Нужна дополнительная проверка ⚠️"
    NON_COMPLIANT = "НЕ СООТВЕТСТВУЕТ ❌"
    INSUFFICIENT_DATA = "НЕДОСТАТОЧНО ДАННЫХ ⚠️"

class UserProfileCreate(BaseModel):
    monthly_budget: confloat(ge=0) = 0.0
    income: Optional[confloat(ge=0)] = None
    investment_style: InvestmentStyle = InvestmentStyle.BALANCED


class UserProfileUpdate(BaseModel):
    monthly_budget: Optional[confloat(ge=0)] = None
    income: Optional[confloat(ge=0)] = None
    investment_style: Optional[InvestmentStyle] = None


class UserProfileResponse(BaseModel):
    user_id: int
    monthly_budget: float
    income: Optional[float]
    investment_style: str
    created_at: datetime
    first_goal_done: bool = False
    first_analysis_done: bool = False
    first_rebalance_done: bool = False
    first_auto_invest_done: bool = False
    welcome_completed: bool = False
    welcome_seen: bool = False

    class Config:
        from_attributes = True

class PositionCreate(BaseModel):
    """Model for creating a position."""
    ticker: str = Field(..., min_length=1, max_length=20)
    quantity: confloat(ge=0)
    average_price: confloat(gt=0)

class PositionUpdate(BaseModel):
    quantity: Optional[confloat(ge=0)] = None
    average_price: Optional[confloat(gt=0)] = None

class PositionResponse(BaseModel):
    id: int
    ticker: str
    quantity: float
    average_price: float
    category_id: int

    class Config:
        from_attributes = True

class PositionData(BaseModel):
    ticker: str
    value: float
    quantity: float
    avg_price: float
    asset_type: Optional[str]
    price: float
    weight: float = 0.0
    pnl_pct: float = 0.0
    pnl_abs: float = 0.0
    shariah_compliant: Optional[bool] = None

class PortfolioCreate(BaseModel):
    cash: confloat(ge=0) = 0.0

class PortfolioResponse(BaseModel):
    id: int
    owner_id: int
    cash: float
    total_value: float
    updated_at: datetime

    class Config:
        from_attributes = True

class PortfolioSettingsCreate(BaseModel):
    monthly_budget: confloat(ge=0) = 0.0
    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    investment_style: InvestmentStyle = InvestmentStyle.BALANCED
    auto_invest_enabled: bool = False

class PortfolioSettingsUpdate(BaseModel):
    monthly_budget: Optional[confloat(ge=0)] = None
    risk_tolerance: Optional[RiskTolerance] = None
    investment_style: Optional[InvestmentStyle] = None
    auto_invest_enabled: Optional[bool] = None

class PortfolioSettingsResponse(BaseModel):
    portfolio_id: int
    monthly_budget: float
    risk_tolerance: str
    investment_style: str
    auto_invest_enabled: bool
    last_auto_invest: Optional[datetime]
    next_auto_invest_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    quantity: confloat(gt=0)
    price: confloat(gt=0)
    is_buy: bool

class TransactionResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    quantity: float
    price: float
    is_buy: bool
    created_at: datetime

    class Config:
        from_attributes = True

class GoalCreate(BaseModel):
    portfolio_id: int
    name: str = Field(..., min_length=1, max_length=200)
    amount: confloat(gt=0)
    years: int = Field(..., ge=1, le=50)
    priority: int = Field(..., ge=1, le=10)
    compliance: str = Field(..., max_length=50)

class GoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[confloat(gt=0)] = None
    years: Optional[int] = Field(None, ge=1, le=50)
    priority: Optional[int] = Field(None, ge=1, le=10)
    compliance: Optional[str] = Field(None, max_length=50)

class GoalResponse(BaseModel):
    id: int
    portfolio_id: int
    name: str
    amount: float
    years: int
    priority: int
    compliance: str

    class Config:
        from_attributes = True

class GoalResult(BaseModel):
    goal_id: int
    goal_name: str
    success_probability: float
    expected_value: float
    shortfall_risk: float
    recommended_monthly: float

class StockInfoResponse(BaseModel):
    name: Optional[str]
    ticker: str
    debt_to_equity: Optional[float]
    pe: Optional[float]
    eps: Optional[float]
    market_cap: Optional[float]
    industry: Optional[str]
    sector: Optional[str]
    dividends: Optional[float]
    earnings_date: Optional[datetime]
    price: float
    growth: Dict[str, Optional[float]]
    receivables: Optional[float]
    total_debt: Optional[float]
    total_cash: Optional[float]
    total_assets: Optional[float]
    revenue: Optional[float]
    interest_income: Optional[float]
    financials_updated_at: Optional[datetime]
    ebitda: Optional[float]
    error: Optional[str] = None

class ETFInfoResponse(BaseModel):
    name: str
    ticker: str
    nav: Optional[float]
    net_assets: Optional[float]
    pe: Optional[float]
    expense: Optional[float]
    price: float
    growth: Dict[str, Optional[float]]
    error: Optional[str] = None

class MarketPriceResponse(BaseModel):
    ticker: str
    price: float
    volume: Optional[float]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    updated_at: datetime

class Holding(BaseModel):
    ticker: str
    weight: confloat(ge=0, le=1)

class RiskMetrics(BaseModel):
    volatility: Optional[float]
    drawdown: Optional[float]
    beta: Optional[float]
    sharpe: Optional[float]
    risk_score: Optional[float]
    risk_label: str

class PortfolioRiskMetrics(BaseModel):
    volatility: Optional[float]
    diversification: Optional[float]
    concentration: str
    risk_score: Optional[float]

class RiskAlert(BaseModel):
    message: str
    severity: Literal["low", "medium", "high"]

class RatioCheck(BaseModel):
    name: str
    status: str
    value: Optional[float]
    limit: float
    buffer_limit: float
    formula: str
    numerator: Optional[float]
    denominator: Optional[float]
    denominator_type: str
    message: str
    missing_fields: List[str]
    source_fields: List[str]

class BusinessCheck(BaseModel):
    status: str
    message: str
    matched_keyword: Optional[str]

class DataFreshness(BaseModel):
    status: str
    days_old: Optional[int]

class ShariahAudit(BaseModel):
    standard: str
    business: BusinessCheck
    checks: List[RatioCheck]
    freshness: DataFreshness
    missing_fields: List[str]

class ShariahScreeningResult(BaseModel):
    status: str
    audit: ShariahAudit
    confidence: float

class ETFShariahResult(BaseModel):
    status: str
    score: int
    halal_percent: float
    trust_score: float
    trust_breakdown: List[Dict[str, Any]]
    halal_stocks: Optional[int]
    haram_stocks: int
    total_analyzed: int
    covered_percent: float
    note: Optional[str] = None
    reason: Optional[str] = None

class PurificationBreakdown(BaseModel):
    ticker: str
    amount: float

class PurificationResult(BaseModel):
    total_purification: float
    breakdown: List[PurificationBreakdown]

class Trade(BaseModel):
    ticker: str
    action: Literal["BUY", "SELL"]
    amount: confloat(gt=0)
    quantity: Optional[float] = None

class RebalancePlan(BaseModel):
    current_weights: Dict[str, float]
    target_weights: Dict[str, float]
    trades: List[Trade]
    estimated_cost: float
    expected_drift: float

class RebalanceExecution(BaseModel):
    success: bool
    message: str
    executed_trades: List[str]
    portfolio_value_after: Optional[float]

class AutoInvestItem(BaseModel):
    ticker: str
    amount: confloat(gt=0)
    reason: str

class AutoInvestPlan(BaseModel):
    monthly_total: float
    items: List[AutoInvestItem]
    target_allocation: Dict[str, float]

class AnalyticsEventCreate(BaseModel):
    user_id: int
    event_name: str = Field(..., min_length=1, max_length=80)
    category: Optional[str] = Field(None, max_length=30)
    event_version: int = 1
    source_attribution: Optional[str] = Field(None, max_length=50)
    duration_ms: Optional[int] = None
    success: bool = True
    event_data: Optional[Dict[str, Any]] = None

class AnalyticsEventResponse(BaseModel):
    id: int
    user_id: int
    event_name: str
    category: Optional[str]
    event_version: int
    source_attribution: Optional[str]
    duration_ms: Optional[int]
    success: bool
    event_data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class DailyAnalyticsSnapshot(BaseModel):
    date: date
    dau: int
    portfolio_opens: int
    auto_invest_execs: int
    avg_response_time: float
    retention_d1: float
    retention_d7: float
    activation_rate: float
    rebalance_adoption: float
    ai_engagement_rate: float
    auto_invest_conversion: float
    avg_portfolio_size: float
    avg_goals_per_user: float
    churn_risk_rate: float

    class Config:
        from_attributes = True

class UserReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1, max_length=2000)

class UserReviewResponse(BaseModel):
    id: int
    user_id: int
    rating: int
    text: str
    created_at: datetime
    published: bool
    admin_note: Optional[str]

    class Config:
        from_attributes = True

class ReferralCodeResponse(BaseModel):
    owner_id: int
    code: str
    clicks: int
    uses: int
    reward_given: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReferralResponse(BaseModel):
    id: int
    inviter_id: int
    invited_id: int
    rewarded: bool
    created_at: datetime

    class Config:
        from_attributes = True

class MarketRegime(BaseModel):
    regime: str
    score: float
    trend: Literal["bull", "bear", "sideways"]
    volatility_level: Literal["low", "medium", "high"]
    confidence: float

class SectorExposure(BaseModel):
    sector: str
    weight: float


class PortfolioAnalysis(BaseModel):
    positions_data: List[PositionData]
    total_value: float
    risk: PortfolioRiskMetrics
    sector_exposure: Dict[str, float]
    top_sector: Optional[str]
    top_sector_weight: float
    top_gainers: List[PositionData]
    top_losers: List[PositionData]
    alerts: List[str]
    market_regime: str
    regime_score: float
    shariah_compliance: Optional[str]
    purification: Optional[PurificationResult]

class ErrorResponse(BaseModel):
    error: str
    error_type: str
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None