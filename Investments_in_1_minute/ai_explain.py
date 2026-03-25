import os
import time
from openai import AsyncOpenAI
from cache import make_cache_key, get_cache, set_cache

MAX_ASSETS_FOR_AI = 8
DAILY_LIMIT = 5

client = AsyncOpenAI(api_key=os.getenv("API_KEY"))

USER_LIMITS = {}


async def explain_portfolio_ai(positions_data, risk, monte_carlo):

    if not positions_data:
        return "No data to analyze."


    positions_data = sorted(
        positions_data,
        key=lambda x: x.get("value", 0),
        reverse=True
    )[:MAX_ASSETS_FOR_AI]

    cache_key = make_cache_key(positions_data, risk, monte_carlo)

    cached = get_cache(cache_key)
    if cached:
        return cached

    positions_str = "\n".join([
        f"{p['ticker']}: {round(p.get('weight', 0)*100,1)}%"
        for p in positions_data
    ])

    prompt = f"""
Portfolio:
{positions_str}

Risk: vol {risk.get('volatility', 0)}, score {risk.get('risk_score', 0)}
Return: {monte_carlo.get('expected_return', 0)}%, worst {monte_carlo.get('worst_case', 0)}%

Explain simply + give exactly 3 actionable improvements.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt.strip()}],
            temperature=0.4,
            max_tokens=180
        )

        result = response.choices[0].message.content

        set_cache(cache_key, result)

        return result

    except Exception:
        return "⚠️ AI temporarily unavailable. Try later."


def check_user_limit(user_id):

    now = int(time.time() // 86400)

    if user_id not in USER_LIMITS:
        USER_LIMITS[user_id] = {"day": now, "count": 0}

    if USER_LIMITS[user_id]["day"] != now:
        USER_LIMITS[user_id] = {"day": now, "count": 0}

    if USER_LIMITS[user_id]["count"] >= DAILY_LIMIT:
        return False

    USER_LIMITS[user_id]["count"] += 1
    return True