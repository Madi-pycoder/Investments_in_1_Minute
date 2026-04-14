from market import get_stocks_batch

FORBIDDEN_KEYWORDS = [
    "bank",
    "financial services",
    "credit",
    "insurance",
    "gambling",
    "casino",
    "betting",
    "alcohol",
    "brewery",
    "tobacco",
    "porn",
    "adult",
    "weapons",
    "defense",
    "capital markets",
    "asset management",
    "mortgage",
    "reit",
    "lending",
    "consumer finance"
]


AAOIFI_LIMITS = {
    "debt": 0.30,
    "cash": 0.30,
    "receivables": 0.49,
    "interest": 0.05
}


def check_business(industry, sector):

    if not industry and not sector:
        return False, "Unknown business"

    text = f"{industry} {sector}".lower()

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in text:
            return False, f"Haram industry ({keyword})"

    return True, "Halal industry"


def safe_ratio(value, total):
    if value is None or total is None or total == 0:
        return None
    return value / total


def check_debt(total_debt, market_cap):
    ratio = safe_ratio(total_debt, market_cap)

    if ratio is None:
        return True, "No debt data (neutral)", None

    if ratio < AAOIFI_LIMITS["debt"]:
        return True, f"{ratio:.2%} OK", ratio

    return False, f"{ratio:.2%} too high", ratio


def check_cash(total_cash, market_cap):

    ratio = safe_ratio(total_cash, market_cap)

    if ratio is None:
        return True, "No cash data (neutral)", None

    if ratio < AAOIFI_LIMITS["cash"]:
        return True, f"{ratio:.2%} OK", ratio

    return False, f"{ratio:.2%} too high", ratio



def calculate_score(results):

    score = 0
    max_score = 4

    if results["business"]:
        score += 1

    if results["debt"]:
        score += 1

    if results["cash"]:
        score += 1

    if results["data_quality"]:
        score += 1

    percent = int((score / max_score) * 100)



    return percent


def calculate_data_quality(stock):

    fields = [
        stock.get("market_cap"),
        stock.get("total_debt"),
        stock.get("total_cash"),
        stock.get("receivables")
    ]

    filled = sum(field is not None for field in fields)
    quality = filled / len(fields)

    return quality



def shariah_screen(stock):

    data_quality = calculate_data_quality(stock)

    business_ok, business_msg = check_business(
        stock.get("industry"),
        stock.get("sector")
    )

    debt_ok, debt_msg, debt_ratio = check_debt(
        stock.get("total_debt"),
        stock.get("market_cap")
    )

    cash_ok, cash_msg, cash_ratio = check_cash(
        stock.get("total_cash"),
        stock.get("total_assets")
    )

    receivables_ok, rec_msg, rec_ratio = check_receivables(
        stock.get("receivables"),
        stock.get("total_assets")
    )

    compliant = all([
        business_ok,
        debt_ok,
        cash_ok,
        receivables_ok
    ])

    results = {
        "business": business_ok,
        "debt": debt_ok,
        "cash": cash_ok,
        "receivables": receivables_ok,
        "data_quality": data_quality >= 0.75
    }

    score = calculate_score(results)

    status = "HALAL ✅" if compliant else "NOT HALAL ❌"

    return {

        "status": status,
        "score": score,

        "business_msg": business_msg,
        "debt_msg": debt_msg,
        "cash_msg": cash_msg,
        "receivables_msg": rec_msg,
        "data_quality": round(data_quality * 100, 1),

        "ratios": {
            "debt": debt_ratio,
            "cash": cash_ratio,
            "receivables": rec_ratio
        }

    }





STOCK_CACHE = {}
ETF_CACHE = {}
SHARIAH_ETFS = {
        "SPUS", "HLAL", "SPRE", "SPSK", "UMMA"
    }

async def shariah_screen_etf_full(etf_ticker, get_etf_holdings):
    holdings = await get_etf_holdings(etf_ticker)

    key = etf_ticker

    if key in ETF_CACHE:
        return ETF_CACHE[key]

    print("DEBUG holdings count:", len(holdings) if holdings else 0)

    if holdings is None or len(holdings) == 0:
        return {
            "status": "UNKNOWN ⚠️",
            "score": 0,
            "halal_percent": 0,
            "halal_stocks": 0,
            "haram_stocks": 0,
            "total_analyzed": 0,
            "reason": "No holdings data"
        }

    if etf_ticker.upper() in SHARIAH_ETFS:
        return {
            "status": "HALAL ✅",
            "score": 100,
            "halal_percent": 100,
            "halal_stocks": None,
            "haram_stocks": 0,
            "total_analyzed": None,
            "note": "Pre-screened Shariah ETF"
        }

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


    MAX_WEIGHT_COVERAGE = 0.90
    MAX_STOCKS = 100

    covered_weight = 0

    halal_weight = 0
    total_weight = 0

    halal_count = 0
    haram_count = 0


    stocks_data = await get_stocks_batch(tickers)

    holdings = sorted(holdings, key=lambda x: x["weight"], reverse=True)

    for holding in holdings:

        if covered_weight >= MAX_WEIGHT_COVERAGE:
            break

        ticker = holding["ticker"]

        if ticker in STOCK_CACHE:
            stock = STOCK_CACHE[ticker]
        else:
            stock = stocks_data.get(ticker)
            if stock:
                STOCK_CACHE[ticker] = stock

        if not stock:
            continue

        screening = shariah_screen(stock)

        weight = holding["weight"]

        covered_weight += weight
        total_weight += weight

        if screening.get("status") == "HALAL ✅":
            halal_weight += weight
            halal_count += 1
        else:
            haram_count += 1



    print("Weight covered:", covered_weight)
    total = halal_count + haram_count


    if total_weight == 0:
        return {
            "status": "UNKNOWN ⚠️",
            "score": 0,
            "halal_percent": 0,
            "halal_stocks": halal_count,
            "haram_stocks": haram_count,
            "total_analyzed": total,
            "reason": "Invalid holdings"
        }

    halal_percent = round((halal_weight / total_weight) * 100, 2)


    if halal_percent >= 95:
        status = "HALAL ✅"

    elif halal_percent >= 80:
        status = "MOSTLY HALAL ⚠️"

    elif halal_percent >= 50:
        status = "MIXED ⚠️"

    else:
        status = "NOT HALAL ❌"


    return {
        "status": status,
        "score": int(halal_percent),
        "halal_percent": halal_percent,
        "halal_stocks": halal_count,
        "haram_stocks": haram_count,
        "total_analyzed": total
    }


def check_receivables(receivables, market_cap):

    ratio = safe_ratio(receivables, market_cap)

    if ratio is None:
        return True, "No receivables data (assumed OK)", None

    if ratio < AAOIFI_LIMITS["receivables"]:
        return True, f"{ratio:.2%} OK", ratio

    return False, f"{ratio:.2%} too high", ratio
