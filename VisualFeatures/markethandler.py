import asyncio
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from ProjectDataBase.analytics import AnalyticsService
from MarketFeatures.market import get_etf_holdings, get_stock_info, get_etf_info
from aiogram.fsm.state import State, StatesGroup
from MainMetricsComputingFeatures.shariah import shariah_screen, shariah_screen_etf_full
from MainMetricsComputingFeatures.riskmanagement import get_risk_metrics_cached, calculate_etf_risk
from renderer import format_shariah
from VisualFeatures.charts import generate_asset_growth_graph
from VisualFeatures import keyboards as kb


class Mode(StatesGroup):
    waiting_for_ticker = State()
router = Router()

@router.callback_query(F.data == "stocks")
async def cmd_stocks(callback: CallbackQuery, state: FSMContext):
    print("STOCKS START")
    await state.set_state(Mode.waiting_for_ticker)
    await state.update_data(type="stocks")
    await callback.message.answer(
        "📈 Stock Analyzer\n\n"
        "Enter a stock ticker (AAPL, NVDA, MSFT...)\n\n"
        "You'll get:\n\n"
        "• Risk score\n"
        "• Growth history\n"
        "• Business fundamentals\n"
        "• Shariah screening\n"
        "• Personal assessment",
        reply_markup=kb.popular_stocks)


async def analyze_ticker(message: Message, state: FSMContext):
    mode = await state.get_data()
    mode_type = mode.get("type")
    ticker = message.text.strip().upper()
    if mode_type == "stocks":
        data = await get_stock_info(ticker)
        if "error" in data:
            await message.answer(data["error"])
            return
        screening = await shariah_screen(data)
        risk = await get_risk_metrics_cached(ticker)
        risk_score = risk["risk_score"]
        risk_label = risk["risk_label"]
        why = []
        if screening["status"] != "HALAL ✅":
            why.append("May not meet Islamic investing standards")
        if risk_score < 40:
            why.append("Low risk profile")
        if data["growth"]["1Y"] > 10:
            why.append("Positive long-term trend")
        if not why:
            why.append("Requires further review")
        why_text = "\n".join([f"• {x}" for x in why])
        text = f"""
            📊 {data['name']} ({data['ticker']})

        💵 Price: {data['price']}$
            

        🕌 Shariah Screening:
        
        {format_shariah(screening["status"])}


        📊 Risk Metrics:  {risk_label}({risk_score}/100)
            
            
        🤖 AI Verdict: {why}
            
            
        💡 Key Takeaways
         
            {why_text}
        
        📈 Growth
        • 1Y: {data['growth']['1Y']}%
        • 5Y: {data['growth']['5Y']}%
            
        👇 Next Step:
            """
        await message.answer(text, reply_markup=kb.after_analysis)
        await state.update_data(
            last_ticker=data["ticker"],
            last_price=data["price"])
        asyncio.create_task(
            AnalyticsService.track_event(
                user_id=message.from_user.id,
                event_name="stock_analyzed",
                category="invest",
                event_data={"ticker": ticker}))
        await state.update_data(
            last_ticker=ticker,
            last_price=data["price"],
            last_stock_data=data,
            last_screening=screening,
            last_risk_score=risk_score,
            last_risk_label=risk_label)
        return

    if mode_type == "etfs":
        data = await get_etf_info(ticker)
        if "error" in data:
            await message.answer(data["error"])
            return
        screening = await shariah_screen_etf_full(ticker, get_etf_holdings)
        risk_etf = await calculate_etf_risk(ticker)
        risk = await get_risk_metrics_cached(ticker)
        risk_score = risk["risk_score"]
        why = []
        if screening["status"] != "HALAL ✅":
            why.append("May not meet Islamic investing standards")
        if risk_score < 40:
            why.append("Low risk profile")
        if data["growth"]["1Y"] > 10:
            why.append("Positive long-term trend")
        if not why:
            why.append("Requires further review")
        why_text = "\n".join([f"• {x}" for x in why])


        text = f"""
            🧩 {data['name']} ({data['ticker']})

        💵 Price: {data['price']}$


        🕌 ETF Shariah:
        
        {format_shariah(screening["status"])}


        📊 Risk Metrics {risk_etf['risk_label']}({risk_etf['risk_score']}/100)
            

        💡 Key Takeaways: {why_text}


        📈 Growth

        • 1Y: {data['growth']['1Y']}%
        • 5Y: {data['growth']['5Y']}%
            
        👇 Next Step:
            """
        await message.answer(text, reply_markup=kb.after_analysis)
        await state.update_data(
            last_ticker=ticker,
            last_price=data["price"],
            last_stock_data=data,
            last_screening=screening,
            last_risk_score=risk_etf['risk_score'],
            last_risk_label=risk_etf['risk_label'])
        print("SAVED STATE: ", await state.get_data())
        asyncio.create_task(
            AnalyticsService.track_event(
                user_id=message.from_user.id,
                event_name="etf_analyzed",
                category="invest",
                event_data={"ticker": ticker}))
        return


@router.message(Mode.waiting_for_ticker)
async def ticker_handler(message, state):
    await analyze_ticker(message, state)

@router.callback_query(F.data == "etfs")
async def cmd_etfs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Mode.waiting_for_ticker)
    await state.update_data(type="etfs")
    await callback.message.answer(
        "🧩 ETF Analyzer\n\n"
        "Enter an ETF ticker (VOO, SPY, QQQ...)\n\n"
        "You'll get:\n\n"
        "• Holdings breakdown\n"
        "• Risk profile\n"
        "• Historical performance\n"
        "• Shariah exposure\n"
        "• AI assessment",
        reply_markup=kb.popular_etfs)


@router.callback_query(F.data.startswith("quick_"))
async def quick_ticker(callback: CallbackQuery, state: FSMContext):
    print("QUICK CALLBACK FIRED")
    ticker = callback.data.replace("quick_", "")
    fake_message = callback.message.model_copy(update={"text": ticker})
    try:
        await analyze_ticker(fake_message, state)
    except Exception as e:
        print("QUICK ERROR: ", e)



@router.callback_query(F.data == "deep_audit")
async def deep_analysis_handler(
    callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mode_type = data.get("type")
    print("DEEP AUDIT STATE: ", data)
    ticker = data.get("last_ticker")
    if not ticker:
        await callback.message.answer("⚠️ Analyze an asset first.")
        return
    if mode_type == "stocks":
        stocks_data = await get_stock_info(ticker)
        if "error" in stocks_data:
            await callback.message.answer(data["error"])
            return
        state_data = await state.get_data()
        stock_data = state_data.get("last_stock_data")
        screening = state_data.get("last_screening")
        if not stock_data:
            await callback.message.answer("Analyze an asset first.")
            return
        risk = await get_risk_metrics_cached(ticker)
        vol = risk["volatility"]
        dd = risk["drawdown"]
        beta = risk["beta"]
        sharpe = risk["sharpe"]
        risk_score = risk["risk_score"]
        risk_label = risk["risk_label"]
        audit = screening["audit"]
        audit_text = ""
        for check in audit["checks"]:
            icon = {
                "pass": "✅",
                "borderline": "⚠️",
                "fail": "❌",
                "neutral": "➖"}[check["status"]]
            value = (
                f"{check['value']:.2%}"
                if check["value"] is not None
                else "N/A")
            audit_text += (
                f"{icon} {check['name']}\n"
                f"• Value: {value}\n"
                f"• Limit: {check['limit']:.0%}\n"
                f"• Formula: {check['formula']}\n"
                f"• Result: {check['message']}\n\n")
        freshness = audit["freshness"]
        days_old = freshness.get("days_old")
        if days_old is None:
            freshness_text = freshness["status"].upper()
        else:
            freshness_text = (
                f"{freshness['status'].upper()} "
                f"({days_old}d old)")
        missing = audit["missing_fields"]
        missing_text = (
            ", ".join(missing)
            if missing
            else "None")
        text = f"""
            📊 {stocks_data['name']} ({stocks_data['ticker']})

            📘 Fundamentals
            • Debt/Equity: {stocks_data['debt_to_equity']}
            • P/E: {stocks_data['pe']}
            • EPS: {stocks_data['eps']}
            • Market Cap: {stocks_data['market_cap']}
            • Dividends: {stocks_data['dividends']}$
            • Earnings: {stocks_data['earnings_date']}

            🕌 Shariah Audit

            Status: {screening['status']}

            📚 Standard:

            • {audit['standard']}

            🏢 Business Screen

            • {audit['business']['message']}

            📊 Financial Audit

                {audit_text}

            🕒 Data Freshness

            • {freshness_text}

            🧩 Missing Data

            • {missing_text}



            📊 Risk Metrics

            • Volatility: {vol}%
            • Max Drawdown: {dd}%
            • Beta: {beta}
            • Sharpe Ratio: {sharpe}

            • Risk Level: {risk_label}
            • Risk Score: {risk_score}/100


            📈 Growth
            • 1D: {stocks_data['growth']['1D']}%
            • 5D: {stocks_data['growth']['5D']}%
            • 1M: {stocks_data['growth']['1M']}%
            • 6M: {stocks_data['growth']['6M']}%
            • 1Y: {stocks_data['growth']['1Y']}%
            • 5Y: {stocks_data['growth']['5Y']}%
            """
        await callback.message.answer(text, reply_markup=kb.after_analysis)

    if mode_type == "etfs":
        data = await get_etf_info(ticker)
        if "error" in data:
            await callback.message.answer(data["error"])
            return
        screening = await shariah_screen_etf_full(
            ticker,
            get_etf_holdings)
        risk = await calculate_etf_risk(ticker)
        top_holdings_text = ""
        for item in screening.get("trust_breakdown", [])[:5]:
            status_icon = {
                "HALAL ✅": "✅",
                "MOSTLY HALAL ⚠️": "⚠️",
                "MIXED ⚠️": "⚠️",
                "NOT HALAL ❌": "❌"}.get(item["status"], "➖")
            trust_percent = round(item["trust"] * 100, 1)
            effective = round(item["effective_weight"] * 100, 2)
            top_holdings_text += (
                f"{status_icon} {item['ticker']}\n"
                f"• Status: {item['status']}\n"
                f"• Portfolio Weight: {item['weight']:.2%}\n"
                f"• Trust: {trust_percent}%\n"
                f"• Effective Halal Weight: {effective}%\n\n")

        text = f"""
            🧩 {data['name']} ({data['ticker']})

            💵 Price: {data['price']}$

            📦 ETF Data
            NAV: {data['nav']}
            Net Assets: {data['net_assets']}
            P/E: {data['pe']}
            Expense Ratio: {data['expense']}

            🕌 ETF Shariah Audit

            Status: {screening['status']}

            Halal Exposure: {screening['halal_percent']}%
            Trust Score: {screening['trust_score']}/100

            📚 Screening Coverage

            • Holdings analyzed: {screening['total_analyzed']}

            • Portfolio coverage: {screening['covered_percent']}%

            • Methodology: TOP-weighted holdings screening

            Top Holdings Audit:

            {top_holdings_text}

            📊 Risk Metrics

            • Volatility: {risk['volatility']}%
            • Max Drawdown: {risk['drawdown']}%
            • Beta: {risk['beta']}
            • Sharpe Ratio: {risk['sharpe']}

            • Risk Level: {risk['risk_label']}
            • Risk Score: {risk['risk_score']}/100


            📈 Growth

            • 1D: {data['growth']['1D']}%
            • 5D: {data['growth']['5D']}%
            • 1M: {data['growth']['1M']}%
            • 6M: {data['growth']['6M']}%
            • 1Y: {data['growth']['1Y']}%
            • 5Y: {data['growth']['5Y']}%
            """
        await callback.message.answer(text, reply_markup=kb.after_analysis)
        from aiogram.types import BufferedInputFile
        chart = await generate_asset_growth_graph(ticker)
        if chart:
            photo = BufferedInputFile(
                chart.read(),
                filename=f"{ticker}.png")
            await callback.message.answer_photo(
                photo,
                caption=f"📈 {ticker} Price Chart (1Y)")
        data_state = await state.get_data()
        ticker = data_state["last_ticker"]
        asyncio.create_task(
            AnalyticsService.track_event(
                user_id=callback.message.from_user.id,
                event_name="etf_analyzed",
                category="invest",
                event_data={"ticker": ticker}))
        return