from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import asyncio
from market import get_stock_info, get_etf_info, get_etf_holdings
from aiogram.fsm.state import State, StatesGroup
from shariah import shariah_screen
from shariah import shariah_screen_etf_full
from riskmanagement import (calculate_volatility, calculate_max_drawdown, calculate_beta,
calculate_risk_score, calculate_sharpe_ratio, get_risk_label, calculate_etf_risk)
from graphs.charts import generate_asset_growth_graph

class Mode(StatesGroup):
    waiting_for_ticker = State()

import keyboards as kb

router = Router()

@router.callback_query(F.data == "stocks")
async def cmd_stocks(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Mode.waiting_for_ticker)
    await state.update_data(type="stocks")

    await callback.message.answer("You chose stocks, now, you can analyze stocks!", show_alert=True)
    await callback.message.answer("Write down the ticker of the stock to start!")

@router.message(Mode.waiting_for_ticker)
async def ticker_handler(message: Message, state: FSMContext):

    mode = await state.get_data()
    mode_type = mode.get("type")

    ticker = message.text.strip().upper()

    if mode_type == "stocks":
        data = await get_stock_info(ticker)

        if "error" in data:
            await message.answer("Тикер не найден 😢")
            return

        screening = shariah_screen(data)
        vol = await calculate_volatility(ticker)
        dd = await calculate_max_drawdown(ticker)
        beta = await calculate_beta(ticker)
        sharpe = await calculate_sharpe_ratio(ticker)
        risk_score = calculate_risk_score(vol, dd, beta, sharpe)
        risk_label = get_risk_label(risk_score)


        text = f"""
        📊 {data['name']} ({data['ticker']})

        💵 Price: {data['price']}$

        📘 Fundamentals
        • Debt/Equity: {data['debt_to_equity']}
        • P/E: {data['pe']}
        • EPS: {data['eps']}
        • Market Cap: {data['market_cap']}
        • Dividends: {data['dividends']}$
        • Earnings: {data['earnings_date']}
        
        🕌 Shariah Screening

        • Status: {screening['status']}
        • Score: {screening['score']}/100

    Financial ratios:
        • Debt: {screening['debt_msg']}
        • Cash: {screening['cash_msg']}

    Business:
        • {screening['business_msg']}
        
        
        
        📊 Risk Metrics

        • Volatility: {vol}%
        • Max Drawdown: {dd}%
        • Beta: {beta}
        • Sharpe Ratio: {sharpe}
        
        • Risk Level: {risk_label}
        • Risk Score: {risk_score}/100
        
    

        📈 Growth
        • 1D: {data['growth']['1D']}%
        • 5D: {data['growth']['5D']}%
        • 1M: {data['growth']['1M']}%
        • 6M: {data['growth']['6M']}%
        • 1Y: {data['growth']['1Y']}%
        • 5Y: {data['growth']['5Y']}%
        """

        await message.answer(text, reply_markup=kb.after_analysis)
        chart = await asyncio.to_thread(generate_asset_growth_graph, ticker)

        if chart:
            from aiogram.types import FSInputFile
            photo = FSInputFile(chart)

            await message.answer_photo(
                photo,
                caption=f"📈 {ticker} Price Chart (1Y)"
            )
        await state.update_data(
            last_ticker=data["ticker"],
            last_price=data["price"]
        )

        return


    if mode_type == "etfs":
        data = await get_etf_info(ticker)

        if "error" in data:
            await message.answer("Тикер не найден 😢")
            return

        screening = await shariah_screen_etf_full(
            ticker,
            get_etf_holdings
        )
        risk = await calculate_etf_risk(ticker)


        text = f"""
        🧩 {data['name']} ({data['ticker']})

        💵 Price: {data['price']}$

        📦 ETF Data
        • NAV: {data['nav']}
        • Net Assets: {data['net_assets']}
        • P/E: {data['pe']}
        • Expense Ratio: {data['expense']}
        
        🕌 Shariah Screening

        • Status: {screening['status']}
        • Halal percentage: {screening['halal_percent']}%
        • Score: {screening['score']}/100
        
        
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

        await message.answer(text, reply_markup=kb.after_analysis)
        chart = await asyncio.to_thread(generate_asset_growth_graph, ticker)

        if chart:
            from aiogram.types import FSInputFile
            photo = FSInputFile(chart)

            await message.answer_photo(
                photo,
                caption=f"📈 {ticker} Price Chart (1Y)"
            )
        await state.update_data(
            last_ticker=data["ticker"],
            last_price=data["price"]
        )

        return


@router.callback_query(F.data == "etfs")
async def cmd_etfs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Mode.waiting_for_ticker)
    await state.update_data(type="etfs")

    await callback.message.answer("You chose ETFs, now, you can analyze ETFs!", show_alert=True),
    await callback.message.answer("Write down the ticker of the ETF to start!")


@router.callback_query(F.data == "analyze_again")
async def analyze_again(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not data.get("type"):
        await callback.message.answer("Choose mode first:", reply_markup=kb.maind)
        return

    await state.set_state(Mode.waiting_for_ticker)
    await callback.answer()
    await callback.message.answer("Enter ticker:")