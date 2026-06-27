import time
from datetime import datetime, timezone
from ProjectDataBase.cache import ETF_CACHE, get_cached, set_cached, ETF_CACHE_TTL
from MarketFeatures.market import get_stocks_batch
import math
import traceback
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
    "market_cap": 2,
    "revenue": 2,
    "total_debt": 2,
    "total_cash": 1,
    "receivables": 1,
    "interest_income": 0}

def clean_number(value):
    if value is None:
        return None
    try:
        value = float(value)
        if math.isnan(value):
            return None
        if math.isinf(value):
            return None
        return value
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

def build_ratio_check(name, numerator_value, denominator_value,
    numerator_field, denominator_field, limit, formula):
    numerator_value = clean_number(numerator_value)
    denominator_value = clean_number(denominator_value)
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
        status = "нейтральный"
        message = "Недостаточно данных для проверки"
    elif ratio <= limit:
        status = "соответствует"
        message = f"{ratio:.2%} - В пределах нормы"
    elif ratio <= limit + BUFFER:
        status = "на грани"
        message = f"{ratio:.2%} - Близко к допустимому пределу"
    else:
        status = "не соответствует"
        message = f"{ratio:.2%} - Превышает допустимый предел"
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
            "status": "Данные устарели",
            "days_old": None}
    now = datetime.now(timezone.utc)
    days_old = (now - updated_at).days
    if days_old <= 90:
        status = "Актуальные данные"
    elif days_old <= 180:
        status = "Данные устаревают"
    else:
        status = "Данные устарели"
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
                "status": "не соответствует",
                "message": f"Запрещённая сфера деятельности: {keyword}",
                "matched_keyword": keyword}
    for keyword in QUESTIONABLE_KEYWORDS:
        if keyword in text:
            return {
                "status": "на грани",
                "message": f"Сомнительная сфера деятельности: {keyword}",
                "matched_keyword": keyword}
    return {
        "status": "соответствует",
        "message": "Сфера деятельности соответствует Шариату",
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
        if value == "соответствует":
            score += weight
        elif value == "на грани":
            score += weight * 0.5
        elif value == "нейтральный":
            score += 0
        elif value == "не соответствует":
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
            "status": "НЕ СООТВЕТСТВУЕТ ❌",
            "audit": {
                "standard": standard,
                "business": {
                    "status": "не соответствует",
                    "message": "Этот актив не проходит критерии"},
                "checks": [],
                "freshness": {
                    "status": "Актуальные данные",
                    "days_old": 0},
                "missing_fields": []},
            "confidence": 100}
    interest_income = clean_number(stock.get("interest_income"))
    if interest_income is None or math.isnan(interest_income):
        interest_check = {
            "name": "Доход от процентов",
            "status": "нейтральный",
            "value": None,
            "limit": config["interest_limit"],
            "formula": "доход от процентов / выручка",
            "message": "Недостаточно данных",
            "missing_fields": ["interest_income"]}
    else:
        interest_check = build_ratio_check(
            name="Доход от процентов",
            numerator_value=interest_income,
            denominator_value=stock.get("revenue"),
            numerator_field="interest_income",
            denominator_field="revenue",
            limit=config["interest_limit"],
            formula="доход от процентов / выручка")
    debt_check = build_ratio_check(
        name="Долговая нагрузка",
        numerator_value=stock.get("total_debt"),
        denominator_value=denominator_value,
        numerator_field="total_debt",
        denominator_field=denominator_field,
        limit=config["debt_limit"],
        formula=f"общий долг / {denominator_field}")
    cash_check = build_ratio_check(
        name="Денежные резервы",
        numerator_value=stock.get("total_cash"),
        denominator_value=denominator_value,
        numerator_field="total_cash",
        denominator_field=denominator_field,
        limit=config["cash_limit"],
        formula=f"все денежные средства / {denominator_field}")
    receivables_value = stock.get("receivables")
    if receivables_value is None:
        receivables_check = {
            "name": "Задолженность клиентов",
            "status": "соответствует",
            "value": None,
            "limit": config["receivables_limit"],
            "formula": f"задолженность / {denominator_field}",
            "message": "Недостаточно данных, использована безопасная оценка",
            "missing_fields": ["receivables"]}
    else:
        receivables_check = build_ratio_check(
            name="Задолженность клиентов",
            numerator_value=stock.get("receivables"),
            denominator_value=denominator_value,
            numerator_field="receivables",
            denominator_field=denominator_field,
            limit=config["receivables_limit"],
            formula=f"задолженность / {denominator_field}")
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
    if business_check["status"] == "не соответствует":
        overall_status = "НЕ СООТВЕТСТВУЕТ ❌"
    elif "не соответствует" in statuses:
        overall_status = "НЕ СООТВЕТСТВУЕТ ❌"
    elif statuses.count("на грани") >= 2:
        overall_status = "Нужна дополнительная проверка ⚠️"
    elif "на грани" in statuses:
        overall_status = "Скорее соответствует Шариату ⚠️"
    else:
        overall_status = "СООТВЕТСТВУЕТ ШАРИАТУ ✅"
    data_quality = calculate_data_quality(stock)
    borderline_count = statuses.count("на грани")
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
            if check["name"] == "Доход от процентов":
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
    if results["business"] == "не соответствует":
        return "НЕ СООТВЕТСТВУЕТ ❌"
    if score >= 80:
        return "СООТВЕТСТВУЕТ ШАРИАТУ ✅"
    if score >= 60:
        return "Скорее соответствует Шариату ⚠️️"
    if score >= 40:
        return "Нужна дополнительная проверка ⚠️"
    return "НЕ СООТВЕТСТВУЕТ ❌"


SHARIAH_ETFS = {"SPUS", "HLAL", "SPRE", "SPSK", "UMMA", "SPTE", "SPWO", "ISDE", "GLD"}
def calculate_stock_trust(screening):
    audit = screening["audit"]
    freshness = audit["freshness"]["status"]
    missing_count = len(audit["missing_fields"])
    confidence = screening.get("confidence", 50)
    trust = confidence / 100
    if freshness == "Данные устаревают":
        trust *= 0.85
    if freshness == "Данные устарели":
        trust *= 0.6
    trust *= max(0.4, 1 - (missing_count * 0.1))
    if screening["status"] == "Нужна дополнительная проверка ⚠️":
        trust *= 0.7
    if screening["status"] == "НЕ СООТВЕТСТВУЕТ ❌":
        trust *= 0.2
    return round(trust, 2)

async def shariah_screen_etf_full(etf_ticker, get_etf_holdings):
    key = etf_ticker.upper()
    start = time.perf_counter()
    cached = get_cached(ETF_CACHE, key, ETF_CACHE_TTL)
    if cached:
        return cached
    holdings = await get_etf_holdings(etf_ticker)
    if holdings is None or len(holdings) == 0:
        return {
            "status": "НЕДОСТАТОЧНО ДАННЫХ ⚠️",
            "score": 0,
            "halal_percent": 0,
            "trust_score": 0,
            "trust_breakdown": [],
            "halal_stocks": 0,
            "haram_stocks": 0,
            "total_analyzed": 0,
            "covered_percent": 0,
            "reason": "Не удалось получить состав ETF"}
    if key in SHARIAH_ETFS:
        return {
            "status": "СООТВЕТСТВУЕТ ШАРИАТУ ✅",
            "score": 100,
            "halal_percent": 100,
            "trust_score": 95,
            "trust_breakdown": [],
            "halal_stocks": None,
            "haram_stocks": 0,
            "total_analyzed": None,
            "covered_percent": 100,
            "note": "ETF уже прошёл критерии"}
    holdings = sorted(holdings, key=lambda x: x["weight"], reverse=True)
    filtered = []
    covered = 0
    for h in holdings:
        if covered >= 0.90 or len(filtered) >= 30:
            break
        filtered.append(h)
        covered += h["weight"]
    holdings = filtered
    tickers = [h["ticker"] for h in holdings]
    STATUS_WEIGHTS = {
        "СООТВЕТСТВУЕТ ШАРИАТУ ✅": 1.0,
        "Скорее соответствует Шариату ⚠️": 0.7,
        "Нужна дополнительная проверка ⚠️": 0.4,
        "НЕ СООТВЕТСТВУЕТ ❌": 0}
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
        if stock_status in ["СООТВЕТСТВУЕТ ШАРИАТУ ✅", "Скорее соответствует Шариату ⚠️"]:
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
            "status": "НЕДОСТАТОЧНО ДАННЫХ ⚠️",
            "score": 0,
            "halal_percent": 0,
            "trust_score": 0,
            "trust_breakdown": [],
            "halal_stocks": halal_count,
            "haram_stocks": haram_count,
            "total_analyzed": 0,
            "covered_percent": 0,
            "reason": "Некорректные данные по составу ETF"}
    halal_percent = round((halal_weight / total_weight) * 100, 2)
    if halal_percent >= 95:
        status = "СООТВЕТСТВУЕТ ШАРИАТУ ✅"
    elif halal_percent >= 80:
        status = "Скорее соответствует Шариату ⚠️"
    elif halal_percent >= 50:
        status = "Нужна дополнительная проверка ⚠️"
    else:
        status = "НЕ СООТВЕТСТВУЕТ ❌"
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
    print("ETF INFO-Shariah:", time.perf_counter() - start)
    return result


def calculate_shariah_status(positions_data):
    haram_assets = [
        p["ticker"]
        for p in positions_data
        if p.get("shariah_compliant") is False]
    if not haram_assets:
        return "Портфель соответствует Шариату ✅"
    if len(haram_assets) == 1:
        return f"Есть спорные активы ⚠️️ ({haram_assets[0]})"
    return f"Есть спорные активы ⚠️ ({len(haram_assets)} шт.)"