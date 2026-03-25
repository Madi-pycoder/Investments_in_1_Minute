import hashlib
import json
import time

CACHE = {}
CACHE_TTL = 60 * 60


def make_cache_key(positions_data, risk, monte_carlo):

    normalized_positions = [
        {
            "ticker": p["ticker"],
            "weight": round(p.get("weight", 0), 2)
        }
        for p in positions_data
    ]

    payload = {
        "positions": sorted(normalized_positions, key=lambda x: x["ticker"]),
        "risk": round(risk.get("volatility", 0), 1),
        "return": round(monte_carlo.get("expected_return", 0), 1)
    }

    raw = json.dumps(payload, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def get_cache(key):
    entry = CACHE.get(key)

    if not entry:
        return None

    if time.time() - entry["time"] > CACHE_TTL:
        del CACHE[key]
        return None

    return entry["value"]


def set_cache(key, value):


    if len(CACHE) > 1000:
        CACHE.clear()

    CACHE[key] = {
        "value": value,
        "time": time.time()
    }