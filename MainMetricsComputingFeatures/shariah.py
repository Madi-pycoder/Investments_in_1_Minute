from datetime import datetime, timezone
from ProjectDataBase.cache import ETF_CACHE, get_cached, set_cached, ETF_CACHE_TTL
from MarketFeatures.market import get_stocks_batch

FORBIDDEN_KEYWORDS = [
    "bank",
    "credit",
    "insurance",
    "casino",
    "gambling",
    "betting",
    "alcohol",
    "brewery",
    "tobacco",
    "porn",
    "adult",
    "weapons",
    "defense",
    "mortgage",
    "reit",
    "lending",
    "consumer finance"]
QUESTIONABLE_KEYWORDS = [
    "financial services",
    "capital markets",
    "asset management"]
FORCED_HARAM = {
    "SPY",
    "VOO",
    "IVV",
    "BRK-B",
    "BRK.B"}
STANDARD_CONFIG = {
    "AAOIFI": {
        "debt_limit": 0.30,
        "cash_limit": 0.30,
        "receivables_limit": 0.49,
        "interest_limit": 0.05,
        "denominator": "market_cap"},
    "MSCI": {
        "debt_limit": 0.33,
        "cash_limit": 0.33,
        "receivables_limit": 0.49,
        "interest_limit": 0.05,
        "denominator": "total_assets"}}
BUFFER = 0.02
WEIGHTS = {
    "business": 3,
    "debt": 2,
    "interest": 2,
    "cash": 1.5,
    "receivables": 1.5,
    "data_quality": 1}

def build_ratio_check(
    name,
    numerator_value,
    denominator_value,
    numerator_field,
    denominator_field,
    limit,
    formula):
    missing_fields = []
    if numerator_value is None:
        missing_fields.append(numerator_field)
    if denominator_value is None:
        missing_fields.append(denominator_field)
    if numerator_value is None or denominator_value is None or denominator_value == 0:
        ratio = None
    else:
        ratio = numerator_value / denominator_value
    if ratio is None:
        status = "neutral"
        message = "Missing financial data"
    elif ratio <= limit:
        status = "pass"
        message = f"{ratio:.2%} within limit"
    elif ratio <= limit + BUFFER:
        status = "borderline"
        message = f"{ratio:.2%} near limit"
    else:
        status = "fail"
        message = f"{ratio:.2%} exceeds limit"
    return {
        "name": name,
        "status": status,
        "value": ratio,
        "limit": limit,
        "buffer_limit": limit + BUFFER,
        "formula": formula,
        "numerator": numerator_value,
        "denominator": denominator_value,
        "denominator_type": denominator_field,
        "message": message,
        "missing_fields": missing_fields,
        "source_fields": [
            numerator_field,
            denominator_field]}

def calculate_data_freshness(stock):
    updated_at = stock.get("financials_updated_at")
    if not updated_at:
        return {
            "status": "stale",
            "days_old": None}
    now = datetime.now(timezone.utc)
    days_old = (now - updated_at).days
    if days_old <= 90:
        status = "fresh"
    elif days_old <= 180:
        status = "aging"
    else:
        status = "stale"
    return {
        "status": status,
        "days_old": days_old}

def get_denominator(stock, standard="AAOIFI"):
    config = STANDARD_CONFIG.get(standard)
    denominator_type = config["denominator"]
    if denominator_type == "market_cap":
        return stock.get("market_cap"), "market_cap"
    if denominator_type == "total_assets":
        return stock.get("total_assets"), "total_assets"
    return None, "unknown"

def check_business(industry, sector):
    text = f"{industry or ''} {sector or ''}".lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in text:
            return {
                "status": "fail",
                "message": f"Forbidden industry: {keyword}",
                "matched_keyword": keyword}
    for keyword in QUESTIONABLE_KEYWORDS:
        if keyword in text:
            return {
                "status": "borderline",
                "message": f"Questionable industry: {keyword}",
                "matched_keyword": keyword}
    return {
        "status": "pass",
        "message": "Business activity appears compliant",
        "matched_keyword": None}

def calculate_purification(dividends, interest_ratio, position_value=None):
    if interest_ratio is None:
        return 0
    if dividends is None:
        return 0
    if dividends < 1:
        if not position_value:
            return 0
        dividend_income = position_value * dividends
    else:
        dividend_income = dividends
    if dividend_income is None:
        return None
    return dividend_income * interest_ratio


def calculate_data_quality(stock):
    weights = {
        "market_cap": 2,
        "revenue": 2,
        "total_debt": 2,
        "total_cash": 1,
        "receivables": 1}
    earned = 0
    possible = sum(weights.values())
    for field, weight in weights.items():
        if stock.get(field) is not None:
            earned += weight
    return earned/possible

def calculate_score(results):
    total_weight = sum(WEIGHTS.values())
    score = 0
    for key, weight in WEIGHTS.items():
        value = results.get(key)
        if value == "pass":
            score += weight
        elif value == "borderline":
            score += weight * 0.5
        elif value == "neutral":
            score += 0
        elif value == "fail":
            score -= weight * 0.5
    percent = int((score / total_weight) * 100)
    return percent


def calculate_confidence(data_quality, borderline_count):
    base = data_quality
    penalty = borderline_count * 0.1
    confidence = max(0, base - penalty)
    return round(confidence * 100, 1)



async def shariah_screen(stock, standard="AAOIFI"):
    config = STANDARD_CONFIG[standard]
    denominator_field = config["denominator"]
    denominator_value = stock.get(denominator_field)
    business_check = check_business(
        stock.get("industry"),
        stock.get("sector"))
    ticker = (stock.get("ticker") or "").upper()
    if ticker in FORCED_HARAM:
        return {
            "status": "NOT HALAL ❌",
            "audit": {
                "standard": standard,
                "business": {
                    "status": "fail",
                    "message": "Known non-Shariah asset"
                },
                "checks": [],
                "freshness": {
                    "status": "fresh",
                    "days_old": 0
                },
                "missing_fields": []
            },
            "confidence": 100
        }
    interest_income = stock.get("interest_income")
    if interest_income is None:
        total_cash = stock.get("total_cash")
        if total_cash is not None:
            interest_income = total_cash * 0.03
    debt_check = build_ratio_check(
        name="Debt Ratio",
        numerator_value=stock.get("total_debt"),
        denominator_value=denominator_value,
        numerator_field="total_debt",
        denominator_field=denominator_field,
        limit=config["debt_limit"],
        formula=f"total_debt / {denominator_field}")
    cash_check = build_ratio_check(
        name="Cash Ratio",
        numerator_value=stock.get("total_cash"),
        denominator_value=denominator_value,
        numerator_field="total_cash",
        denominator_field=denominator_field,
        limit=config["cash_limit"],
        formula=f"total_cash / {denominator_field}")
    receivables_check = build_ratio_check(
        name="Receivables Ratio",
        numerator_value=stock.get("receivables"),
        denominator_value=denominator_value,
        numerator_field="receivables",
        denominator_field=denominator_field,
        limit=config["receivables_limit"],
        formula=f"receivables / {denominator_field}")
    interest_check = build_ratio_check(
        name="Interest Income Ratio",
        numerator_value=interest_income,
        denominator_value=stock.get("revenue"),
        numerator_field="interest_income",
        denominator_field="revenue",
        limit=config["interest_limit"],
        formula="interest_income / revenue")
    checks = [
        debt_check,
        cash_check,
        receivables_check,
        interest_check]
    missing_fields = []
    for check in checks:
        missing_fields.extend(check["missing_fields"])
    freshness = calculate_data_freshness(stock)
    statuses = [x["status"] for x in checks]
    if business_check["status"] == "fail":
        overall_status = "NOT HALAL ❌"
    elif "fail" in statuses:
        overall_status = "NOT HALAL ❌"
    elif statuses.count("borderline") >= 2:
        overall_status = "MIXED ⚠️"
    elif "borderline" in statuses:
        overall_status = "MOSTLY HALAL ⚠️"
    else:
        overall_status = "HALAL ✅"
    data_quality = calculate_data_quality(stock)
    borderline_count = statuses.count("borderline")
    confidence = calculate_confidence(
        data_quality,
        borderline_count)
    audit = {
        "standard": standard,
        "business": business_check,
        "checks": checks,
        "freshness": freshness,
        "missing_fields": list(set(missing_fields))}
    return {
        "status": overall_status,
        "audit": audit,
        "confidence": confidence}


async def calculate_portfolio_purification(positions, stocks_data):
    total_purification = 0
    breakdown = []
    for p in positions:
        ticker = p["ticker"]
        value = p["value"]
        stock = stocks_data.get(ticker)
        if not stock:
            continue
        screening = await shariah_screen(stock)
        interest_ratio = None
        for check in screening["audit"]["checks"]:
            if check["name"] == "Interest Income Ratio":
                interest_ratio = check["value"]
                break
        purification = calculate_purification(
            stock.get("dividends"),
            interest_ratio,
            position_value=value)
        if purification is not None:
            total_purification += purification
            breakdown.append({
                "ticker": ticker,
                "amount": purification})
    return {
        "total_purification": round(total_purification, 2),
        "breakdown": breakdown}

def determine_status(results, score):
    if results["business"] == "fail":
        return "NOT HALAL ❌"
    if score >= 80:
        return "HALAL ✅"
    if score >= 60:
        return "MOSTLY HALAL ⚠️"
    if score >= 40:
        return "MIXED ⚠️"
    return "NOT HALAL ❌"


SHARIAH_ETFS = {"SPUS", "HLAL", "SPRE", "SPSK", "UMMA", "SPTE", "SPWO", "ISDE"}
def calculate_stock_trust(screening):
    audit = screening["audit"]
    freshness = audit["freshness"]["status"]
    missing_count = len(audit["missing_fields"])
    confidence = screening.get("confidence", 50)
    trust = confidence / 100
    if freshness == "aging":
        trust *= 0.85
    if freshness == "stale":
        trust *= 0.6
    trust *= max(0.4, 1 - (missing_count * 0.1))
    if screening["status"] == "MIXED ⚠️":
        trust *= 0.7
    if screening["status"] == "NOT HALAL ❌":
        trust *= 0.2
    return round(trust, 2)

async def shariah_screen_etf_full(etf_ticker, get_etf_holdings):
    key = etf_ticker.upper()
    cached = get_cached(ETF_CACHE, key, ETF_CACHE_TTL)
    if cached:
        return cached
    holdings = await get_etf_holdings(etf_ticker)
    if holdings is None or len(holdings) == 0:
        return {
            "status": "UNKNOWN ⚠️",
            "score": 0,
            "halal_percent": 0,
            "trust_score": 0,
            "trust_breakdown": [],
            "halal_stocks": 0,
            "haram_stocks": 0,
            "total_analyzed": 0,
            "covered_percent": 0,
            "reason": "No holdings data"}
    if key in SHARIAH_ETFS:
        return {
            "status": "HALAL ✅",
            "score": 100,
            "halal_percent": 100,
            "trust_score": 95,
            "trust_breakdown": [],
            "halal_stocks": None,
            "haram_stocks": 0,
            "total_analyzed": None,
            "covered_percent": 100,
            "note": "Pre-screened Shariah ETF"}
    holdings = sorted(holdings, key=lambda x: x["weight"], reverse=True)
    filtered = []
    covered = 0
    for h in holdings:
        if covered >= 0.90 or len(filtered) >= 100:
            break
        filtered.append(h)
        covered += h["weight"]
    holdings = filtered
    tickers = [h["ticker"] for h in holdings]
    STATUS_WEIGHTS = {
        "HALAL ✅": 1.0,
        "MOSTLY HALAL ⚠️": 0.7,
        "MIXED ⚠️": 0.4,
        "NOT HALAL ❌": 0}
    covered_weight = 0
    halal_weight = 0
    total_weight = 0
    halal_count = 0
    haram_count = 0
    trust_breakdown = []
    stocks_data = await get_stocks_batch(tickers)
    for holding in holdings:
        ticker = holding["ticker"]
        weight = holding["weight"]
        stock = stocks_data.get(ticker)
        if not stock:
            continue
        screening = await shariah_screen(stock)
        stock_status = screening.get("status")
        trust_score = calculate_stock_trust(screening)
        status_multiplier = STATUS_WEIGHTS.get(stock_status, 0)
        effective_weight = weight * trust_score * status_multiplier
        covered_weight += weight
        total_weight += weight
        halal_weight += effective_weight
        if stock_status in ["HALAL ✅", "MOSTLY HALAL ⚠️"]:
            halal_count += 1
        else:
            haram_count += 1
        trust_breakdown.append({
            "ticker": ticker,
            "status": stock_status,
            "weight": weight,
            "trust": trust_score,
            "effective_weight": effective_weight})
    if total_weight == 0:
        return {
            "status": "UNKNOWN ⚠️",
            "score": 0,
            "halal_percent": 0,
            "trust_score": 0,
            "trust_breakdown": [],
            "halal_stocks": halal_count,
            "haram_stocks": haram_count,
            "total_analyzed": 0,
            "covered_percent": 0,
            "reason": "Invalid holdings"}
    halal_percent = round((halal_weight / total_weight) * 100, 2)
    if halal_percent >= 95:
        status = "HALAL ✅"
    elif halal_percent >= 80:
        status = "MOSTLY HALAL ⚠️"
    elif halal_percent >= 50:
        status = "MIXED ⚠️"
    else:
        status = "NOT HALAL ❌"

    result = {
        "status": status,
        "score": int(halal_percent),
        "halal_percent": halal_percent,
        "trust_score": round((halal_weight / total_weight) * 100, 2),
        "trust_breakdown": sorted(
            trust_breakdown, key=lambda x: x["weight"], reverse=True)[:10],
        "halal_stocks": halal_count,
        "haram_stocks": haram_count,
        "total_analyzed": len(trust_breakdown),
        "covered_percent": round(covered_weight * 100, 2),}
    set_cached(ETF_CACHE, key, result)
    return result


def calculate_shariah_status(positions_data):
    haram_assets = [
        p["ticker"]
        for p in positions_data
        if p.get("shariah_compliant") is False]
    if not haram_assets:
        return "Compliant ✅"
    if len(haram_assets) == 1:
        return f"Mixed ⚠️ ({haram_assets[0]})"
    return f"Mixed ⚠️ ({len(haram_assets)} assets)"