from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import StatesGroup, State
from market import get_stock_info, get_stocks_batch
from portoflio_rebalance import calculate_rebalance
from riskmanagement import (calculate_portfolio_risk,
monte_carlo_portfolio, stress_test_portfolio)
from shariah_optimizer import optimize_shariah_portfolio
from ai_explain import explain_portfolio_logic
from goal_engine import (simulate_multiple_goals,
                         optimize_portfolio_for_goals,
                         build_goal_based_weights,)
from Portfolio_info.portfolio_data import load_portfolio_data
from Portfolio_info.portfolio_compute import compute_portfolio_metrics
from Portfolio_info.portfolio_view import build_portfolio_text
from user_profile import get_user_profile, create_user_profile, update_user_profile, get_effective_monthly_budget
from robo_engine import RoboAdvisor
from auto_invest_engine import run_auto_invest_for_user
from financial_brain import FinancialBrain
from graphs.charts import generate_portfolio_growth_graph, generate_sector_allocation_chart
import requets as rq
import keyboards as kb
from requets import get_goals
import asyncio

class GoalSetup(StatesGroup):
    name = State()
    amount = State()
    years = State()
    priority = State()
    compliance = State()

router = Router()


@router.callback_query(F.data == "portfolio")
async def show_portfolio(callback: CallbackQuery, state: FSMContext):

    await callback.message.answer("⚡ Loading...")

    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")

    if not portfolio_id:
        await callback.message.answer("❌ Login first.")
        return

    data = await load_portfolio_data(portfolio_id)

    if not data["positions"]:
        await callback.message.answer(
            f"💰 Cash: ${data['portfolio'].cash}\nNo positions."
        )
        return


    metrics = await compute_portfolio_metrics(data, portfolio_id)

    text = build_portfolio_text(data, metrics)

    regime = metrics.get("market_regime", "unknown")

    regime_map = {
        "bull": "📈 Bull Market — growth phase",
        "bear": "📉 Bear Market — decline phase",
        "crisis": "🚨 Crisis — high volatility",
        "sideways": "➡️ Sideways — no clear trend",
        "unknown": "❓ Unknown market"
    }

    text += f"\n\n🌍 Market Regime:\n{regime_map.get(regime)}"

    await callback.message.answer(text, reply_markup=kb.after_portfolio_action)

    positions_data = metrics["positions_data"]

    growth_graph = await asyncio.to_thread(generate_portfolio_growth_graph, positions_data)

    sector_chart = await asyncio.to_thread(generate_sector_allocation_chart, metrics["sector_exposure"])

    if growth_graph:
        from aiogram.types import FSInputFile

        photo = FSInputFile(growth_graph)

        await callback.message.answer_photo(
            photo,
            caption="📈 Portfolio Growth (1Y)"
        )

    if sector_chart:
        from aiogram.types import FSInputFile

        photo = FSInputFile(sector_chart)

        await callback.message.answer_photo(
            photo,
            caption="📊 Sector Allocation"
        )


price_cache = {}

async def get_price_cached(ticker):
    if ticker in price_cache:
        return price_cache[ticker]

    data = await get_stock_info(ticker)
    price_cache[ticker] = data
    return data


@router.callback_query(F.data == "explain_portfolio")
async def explain_portfolio(callback: CallbackQuery, state: FSMContext):

    await callback.answer("🧠 Running deep analysis...")

    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")

    data = await load_portfolio_data(portfolio_id)

    if not data["positions"]:
        await callback.message.answer("No portfolio data.")
        return


    metrics = await compute_portfolio_metrics(data, portfolio_id)

    positions_data = metrics["positions_data"]
    total_value = metrics["total_value"]


    risk = metrics["risk"]

    mc_task = asyncio.create_task(
        monte_carlo_portfolio(positions_data, simulations=1000)
    )

    stress_task = asyncio.to_thread(
        stress_test_portfolio,
        positions_data
    )

    goals = data.get("goals") or []

    goal_results = None

    if goals:
        goal_results = await asyncio.to_thread(
            simulate_multiple_goals,
            positions_data,
            total_value,
            goals,
            (risk.get("volatility") or 15) / 100
        )

    monte_carlo, stress = await asyncio.gather(
        mc_task,
        stress_task
    )



    explanation = explain_portfolio_logic(
        positions_data,
        risk,
        monte_carlo,
        goals,
        goal_results,
        metrics.get("top_sector"),
        metrics.get("top_sector_weight"),
    )

    text = "🧠 Portfolio Diagnosis\n\n"

    if monte_carlo:
        text += (
            f"📊 Simulation\n"
            f"Expected: {monte_carlo.get('expected_return')}%\n"
            f"Worst: {monte_carlo.get('worst_case')}%\n\n"
        )

    if goal_results:
        text += "🎯 Goals\n\n"

        for r in goal_results:
            g = r["goal"]
            sim = r["simulation"]
            analysis = r["analysis"]

            text += (
                f"{g['name']}\n"
                f"{sim['probability']}% | ${analysis['monthly_needed']}/mo\n\n"
            )

    text += explanation

    await callback.message.answer(text)




async def compare_portfolios(current_positions, target_weights):


    current_risk = await calculate_portfolio_risk(current_positions)
    current_mc = await monte_carlo_portfolio(current_positions)


    total_value = sum(p["value"] for p in current_positions)

    rebalanced_positions = []

    for p in current_positions:
        ticker = p["ticker"]
        target_weight = target_weights.get(ticker, 0)

        rebalanced_positions.append({
            "ticker": ticker,
            "value": total_value * target_weight,
            "weight": target_weight
        })

    rebalanced_risk = await calculate_portfolio_risk(rebalanced_positions)
    rebalanced_mc = await monte_carlo_portfolio(rebalanced_positions)

    return {
        "current": {
            "return": current_mc.get("expected_return"),
            "risk": current_risk.get("volatility")
        },
        "rebalanced": {
            "return": rebalanced_mc.get("expected_return"),
            "risk": rebalanced_risk.get("volatility")
        }
    }





def detect_goal_conflicts(goals):
    warnings = []

    short_term = [g for g in goals if g["years"] <= 3]
    long_term = [g for g in goals if g["years"] >= 7]

    if short_term and long_term:
        warnings.append("⚠️ Mixing short & long-term goals → consider separate portfolios")

    if len(goals) >= 3:
        warnings.append("⚠️ Too many goals → focus capital")

    return warnings





@router.callback_query(F.data == "rebalance_now")
async def rebalance_now(callback: CallbackQuery, state: FSMContext):

    await callback.answer("Calculating rebalance...")

    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")

    positions = await rq.get_positions(portfolio_id)

    if not positions:
        await callback.message.answer("No positions.")
        return

    tickers = [p.ticker for p in positions]

    stocks_batch = await get_stocks_batch(tickers)

    price_tasks = [get_stock_info(t) for t in tickers]
    prices_data = await asyncio.gather(*price_tasks)

    prices_dict = {
        t: float(d["price"])
        for t, d in zip(tickers, prices_data)
        if d and "price" in d
    }


    positions_data = []
    total_value = 0

    for p in positions:
        price = prices_dict.get(p.ticker)

        if not price:
            continue

        value = p.quantity * price
        total_value += value

        positions_data.append({
            "ticker": p.ticker,
            "value": value
        })

    for p in positions_data:
        p["weight"] = p["value"] / total_value if total_value else 0


    goals = await get_goals(portfolio_id)


    has_shariah = any(g.get("compliance") == "shariah" for g in goals)

    if has_shariah:
        target_weights = optimize_shariah_portfolio(
            positions_data,
            stocks_batch
        )
    else:
        n = len(positions_data)
        target_weights = {p["ticker"]: 1 / n for p in positions_data} if n else {}


    trades = calculate_rebalance(positions_data, target_weights, total_value)

    if not trades:
        await callback.message.answer("✅ Portfolio already balanced.")
        return

    text = "⚖️ Rebalance Plan\n\n"

    for t in trades:
        text += f"{t['action']} ${t['amount']} {t['ticker']}\n"

    comparison = await compare_portfolios(
        positions_data,
        target_weights
    )

    if comparison:
        text += "\n📊 Before vs After\n\n"

        text += (
            f"Current:\n"
            f"Return: {comparison['current']['return']}%\n"
            f"Risk: {comparison['current']['risk']}%\n\n"

            f"Rebalanced:\n"
            f"Return: {comparison['rebalanced']['return']}%\n"
            f"Risk: {comparison['rebalanced']['risk']}%\n"
        )

    await rq.execute_rebalance(
        portfolio_id,
        trades,
        prices_dict
    )

    await callback.message.answer("✅ Portfolio rebalanced automatically.")





@router.callback_query(F.data == "rebalance_shariah")
async def rebalance_shariah(callback: CallbackQuery, state: FSMContext):

    await callback.answer("Applying Shariah rebalance...")

    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")

    positions = await rq.get_positions(portfolio_id)

    if not positions:
        await callback.message.answer("No positions.")
        return

    tickers = [p.ticker for p in positions]

    stocks_batch = await get_stocks_batch(tickers)

    price_tasks = [get_stock_info(t) for t in tickers]
    prices_data = await asyncio.gather(*price_tasks)

    prices_dict = {
        t: float(d["price"])
        for t, d in zip(tickers, prices_data)
        if d and "price" in d
    }

    positions_data = []
    total_value = 0

    for p in positions:
        price = prices_dict.get(p.ticker)
        if not price:
            continue

        value = p.quantity * price
        total_value += value

        positions_data.append({
            "ticker": p.ticker,
            "value": value
        })

    for p in positions_data:
        p["weight"] = p["value"] / total_value if total_value else 0

    target_weights = optimize_shariah_portfolio(
        positions_data,
        stocks_batch
    )

    if not target_weights:
        await callback.message.answer("❌ Cannot build Shariah portfolio.")
        return

    trades = calculate_rebalance(positions_data, target_weights, total_value)

    await rq.execute_rebalance(portfolio_id, trades, prices_dict)

    await callback.message.answer("🕌 Shariah rebalance complete.")





@router.callback_query(F.data == "goal_fix")
async def goal_fix(callback: CallbackQuery, state: FSMContext):

    await callback.answer("⚡ Optimizing...")

    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")


    data = await load_portfolio_data(portfolio_id)

    if not data["positions"]:
        await callback.message.answer("No positions.")
        return


    metrics = await compute_portfolio_metrics(data, portfolio_id)

    goals = metrics["goals"]

    if not goals:
        await callback.message.answer(
            "No goals set.\n👉 Add goals first."
        )
        return

    positions_data = metrics["positions_data"]
    total_value = metrics["total_value"]


    risk = metrics["risk"]
    current_vol = (risk.get("volatility") or 15) / 100


    optimizations = await asyncio.to_thread(
        optimize_portfolio_for_goals,
        positions_data,
        total_value,
        goals,
        current_vol
    )

    if not optimizations:
        await callback.message.answer("❌ Cannot optimize.")
        return

    best = optimizations[0]


    target_weights = build_goal_based_weights(
        positions_data,
        goals,
        best["risk"]
    )

    trades = calculate_rebalance(
        positions_data,
        target_weights,
        total_value
    )

    if not trades:
        await callback.message.answer("✅ Already optimal.")
        return


    await rq.execute_rebalance(
        portfolio_id,
        trades,
        data["prices_dict"]
    )


    await callback.message.answer(
        f"🎯 Goal Fix Applied\n\n"
        f"📈 Score: {best['score']}%\n"
        f"⚖️ Risk: {int(best['risk']*100)}%\n"
        f"💰 +${best['monthly_boost']}/mo"
    )



@router.callback_query(F.data == "auto_invest")
async def auto_invest_flow(callback: CallbackQuery, state: FSMContext):

    await callback.answer("🤖 Building your auto-invest plan...")

    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")

    data = await load_portfolio_data(portfolio_id)
    metrics = await compute_portfolio_metrics(data, portfolio_id)

    user_id = callback.from_user.id

    profile = get_user_profile(user_id)
    if not profile:
        profile = create_user_profile(user_id)

    robo = RoboAdvisor(profile, metrics)

    plan = robo.build_auto_invest_plan()

    if not plan:

        issues = robo.get_issues()

        text = "❌ Cannot build plan\n\n"

        for i in issues:
            text += f"• {i}\n"

        await callback.message.answer(text)

        return

    total_value = metrics["total_value"]

    monthly_budget = get_effective_monthly_budget(
        profile,
        total_value
    )

    if monthly_budget <= 0:
        await callback.message.answer(
            "❌ Set your monthly budget first.\n\n"
            "Example: $100–300/month"
        )
        return

    regime = metrics.get("market_regime", "unknown")

    if regime == "bear":
        monthly_budget *= 0.7
    elif regime == "bull":
        monthly_budget *= 1.1

    if not plan:
        await callback.message.answer(
            "❌ Cannot build plan.\n\n"
            "Possible reasons:\n"
            "• No goals set\n"
            "• Portfolio already optimal\n"
            "• Not enough data"
        )
        return

    text = "🤖 Auto-Invest Mode\n\n"

    total = sum(x["amount"] for x in plan)

    regime_map = {
        "bull": "📈 Bull Market — growth phase",
        "bear": "📉 Bear Market — decline phase",
        "crisis": "🚨 Crisis — high volatility",
        "sideways": "➡️ Sideways — no clear trend",
        "unknown": "❓ Unknown market"
    }

    text += f"\n\n🌍 Market Regime: {regime_map.get(regime)}"

    text += f"💰 Monthly: ${round(total, 2)}\n\n"

    for x in plan:
        text += f"+ ${x['amount']} → {x['ticker']}\n"


    text += "\n🎯 Optimized for your goals"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Enable Auto-Invest", callback_data="enable_auto_invest")],
        ]
    )

    await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "enable_auto_invest")

async def enable_auto_invest(callback: CallbackQuery):

    user_id = callback.from_user.id

    profile = get_user_profile(user_id)

    if not profile:

        profile = create_user_profile(user_id)

    update_user_profile(user_id, auto_invest_enabled=True)

    await callback.answer()

    await callback.message.answer(

        "✅ Auto-Invest Activated\n\n"

        "Your portfolio will grow automatically every month after running Auto-Invest! 🚀"

    )


@router.callback_query(F.data == "run_auto_now")
async def run_auto_now(callback: CallbackQuery, state: FSMContext):

    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")
    user_id = callback.from_user.id

    result = await run_auto_invest_for_user(user_id, portfolio_id)


    if result["status"] == "executed":

        text = "🚀 Auto-Invest Executed\n\n"

        for t in result["trades"]:
            text += f"BUY ${t['amount']} {t['ticker']}\n"

        await callback.message.answer(text)

    else:
        await callback.message.answer(f"⚠️ {result['status']}")



@router.callback_query(F.data == "what_if")
async def what_if_flow(callback: CallbackQuery, state: FSMContext):

    await callback.answer("Simulating scenarios...")

    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")

    data = await load_portfolio_data(portfolio_id)
    metrics = await compute_portfolio_metrics(data, portfolio_id)

    user_id = callback.from_user.id

    profile = get_user_profile(user_id)
    if not profile:
        profile = create_user_profile(user_id)

    robo = RoboAdvisor(profile, metrics)

    scenarios = robo.run_what_if()

    if not scenarios:
        await callback.message.answer("No goal data.")
        return

    text = "🧮 What If Analysis\n\n"

    for s in scenarios:
        delta = s.get("delta", 0)
        delta_str = f"(+{delta}%)" if delta > 0 else f"({delta}%)"

        text += f"{s['scenario']}: {s['probability']}% {delta_str}\n"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Add $200/mo", callback_data="what_if_boost")],
            [InlineKeyboardButton(text="⏳ Extend Timeline", callback_data="what_if_time")],
        ]
    )

    await callback.message.answer(text, reply_markup=keyboard)




@router.callback_query(F.data == "nudges")
async def nudges_flow(callback: CallbackQuery, state: FSMContext):

    await callback.answer("🧠 AI Coach analyzing...")

    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")

    data = await load_portfolio_data(portfolio_id)
    metrics = await compute_portfolio_metrics(data, portfolio_id)

    user_id = callback.from_user.id

    profile = get_user_profile(user_id)
    if not profile:
        profile = create_user_profile(user_id)

    robo = RoboAdvisor(profile, metrics)

    nudges = robo.get_nudges()

    if not nudges:
        await callback.message.answer("No suggestions.")
        return

    text = "🧠 AI Coach\n\n"

    buttons = []

    for n in nudges:
        emoji = {
            "critical": "🚨",
            "improve": "⚠️",
            "good": "✅"
        }.get(n["type"], "•")

        text += f"{emoji} {n['text']}\n"

        if n["type"] != "good":
            buttons.append(
                [InlineKeyboardButton(
                    text=f"⚡ Fix {n['text'][:10]}",
                    callback_data="goal_fix"
                )]
            )

    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )



@router.callback_query(F.data == "financial_brain")
async def financial_brain_flow(callback: CallbackQuery, state: FSMContext):

    await callback.answer("🧠 Thinking...")

    data_state = await state.get_data()
    portfolio_id = data_state.get("portfolio_id")

    data = await load_portfolio_data(portfolio_id)
    metrics = await compute_portfolio_metrics(data, portfolio_id)

    user_id = callback.from_user.id

    profile = get_user_profile(user_id)
    if not profile:
        profile = create_user_profile(user_id)

    robo = RoboAdvisor(profile, metrics)
    brain = FinancialBrain(robo)

    text = brain.build_summary()

    await callback.message.answer(text)
