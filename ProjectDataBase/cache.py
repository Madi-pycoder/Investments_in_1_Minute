import time
portfolio_data_cache = {}
FX_CACHE = {}
STOCKS_CACHE = {}
portfolio_cache = {}
diagnosis_cache = {}
RETURNS_CACHE = {}
COV_CACHE = {}
hist_cache = {}
PORTFOLIO_VOL_CACHE = {}
STOCK_CACHE = {}
ETF_CACHE = {}
AUTO_INVEST_METRICS_CACHE = {}
rebalance_preview_cache = {}
goal_fix_preview_cache = {}
STOCK_INFO_CACHE = {}
RISK_METRICS_CACHE = {}
PORTFOLIO_VIEW_CACHE = {}
AUTO_INVEST_LOCKS = {}
AUTO_INVEST_INFLIGHT = {}
CACHE_TTL = 300
STOCK_INFO_TTL = 1800
RISK_METRICS_TTL = 3600
ETF_CACHE_TTL = 3600
DIAGNOSIS_TTL = 300
PORTFOLIO_VIEW_TTL = 30
DIAGNOSIS_IN_PROGRESS = set()

def get_cached(cache, key, ttl):
    item = cache.get(key)
    if not item:
        return None
    if time.time() - item["ts"] > ttl:
        cache.pop(key, None)
        return None
    return item["data"]

def set_cached(cache, key, value):
    cache[key] = {"data": value, "ts": time.time()}

def get_cached_diagnosis(portfolio_id):
    item = diagnosis_cache.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > DIAGNOSIS_TTL:
        diagnosis_cache.pop(portfolio_id, None)
        return None
    return item["data"]

def get_portfolio_view_cached(portfolio_id):
    item = PORTFOLIO_VIEW_CACHE.get(portfolio_id)
    if not item:
        return None
    if time.time() - item["ts"] > PORTFOLIO_VIEW_TTL:
        PORTFOLIO_VIEW_CACHE.pop(portfolio_id, None)
        return None
    return item["data"]