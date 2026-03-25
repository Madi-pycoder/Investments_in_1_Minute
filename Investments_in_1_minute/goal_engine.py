import numpy as np

TRADING_DAYS = 252


def calculate_monthly_contribution(current_value, goal, years, rate=0.07):
    months = years * 12
    r = rate / 12

    future_value_current = current_value * (1 + r) ** months

    needed = goal - future_value_current

    if needed <= 0:
        return 0

    monthly = needed / (((1 + r) ** months - 1) / r)

    return round(monthly, 2)


def simulate_goal_probability(
    positions_data,
    current_value,
    goal_amount,
    years,
    portfolio_volatility=None,
    expected_return=None,
    simulations=2000
):


    if not positions_data or current_value <= 0:
        return None


    if expected_return is None:
        expected_return = 0.07

    if portfolio_volatility is None:
        portfolio_volatility = 0.15




    days = years * TRADING_DAYS

    mu = expected_return / TRADING_DAYS
    sigma = portfolio_volatility / np.sqrt(TRADING_DAYS)

    random_returns = np.random.normal(mu, sigma, (simulations, days))

    growth = np.cumprod(1 + random_returns, axis=1)

    final_values = current_value * growth[:, -1]

    success_prob = np.mean(final_values >= goal_amount)

    expected = np.mean(final_values)
    worst = np.percentile(final_values, 5)

    return {
        "probability": round(success_prob * 100, 1),
        "expected": round(expected, 2),
        "worst": round(worst, 2)
    }
