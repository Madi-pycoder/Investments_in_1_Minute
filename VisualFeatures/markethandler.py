import asyncio
import random
import time
import traceback
import pandas as pd
from datetime import datetime
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from ProjectDataBase.analytics import AnalyticsService
from MarketFeatures.market import get_etf_holdings, get_stock_info, get_etf_info
from aiogram.fsm.state import State, StatesGroup
from MainMetricsComputingFeatures.shariah import shariah_screen, shariah_screen_etf_full
from MainMetricsComputingFeatures.riskmanagement import get_risk_metrics_cached, calculate_etf_risk
from VisualFeatures.renderer import format_shariah, format_money, format_percent, risk_bar
from VisualFeatures.charts import generate_asset_growth_graph
from VisualFeatures import keyboards as kb


class Mode(StatesGroup):
    waiting_for_ticker = State()
router = Router()

@router.callback_query(F.data == "stocks")
async def cmd_stocks(callback: CallbackQuery, state: FSMContext):
    print("MARKETHANDLER IMPORTED")
    print("STOCKS START")
    await state.set_state(Mode.waiting_for_ticker)
    await state.update_data(type="stocks")
    await callback.message.answer(
        "📈 Анализ акций\n\n"
        "Покажем:\n"
        "• уровень риска\n"
        "• рост компании\n"
        "• финансовое состояние\n"
        "• проверку на соответствие Шариату\n"
        "• понятный итоговый вывод\n\n"
        "Введите тикер компании\n\n"
        "ИЛИ выберите готовую подборку 👇",
        reply_markup=kb.stock_categories)
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="stock.opened",
            category="funnel"))

@router.callback_query(F.data == "stock_growth")
async def stock_growth(callback: CallbackQuery):
    await callback.message.answer(
        "🚀 Акции роста\n\n"
        "NVDA — AI лидер\n"
        "AMD — AI и чипы\n"
        "TSLA — электромобили\n"
        "META — AI + соцсети\n\n"
        "Нажмите на тикер:",
        reply_markup=kb.growth_stocks)

@router.callback_query(F.data == "stock_shariah")
async def stock_shariah(callback: CallbackQuery):
    await callback.message.answer(
        "🕌 Акции, соответствующие Шариату\n\n"
        "AAPL — Iphone и устройства\n"
        "GOOGL — AI + поисковик\n"
        "TSM — лидер в сфере чипов\n"
        "NVDA — AI лидер\n\n"
        "Нажмите на тикер:",
        reply_markup=kb.shariah_stocks)

@router.callback_query(F.data == "stock_safe")
async def stock_safe(callback: CallbackQuery):
    await callback.message.answer(
        "🛡 Более устойчивые компании\n\n"
        "BRK-B — инвестиционный лидер\n"
        "MSFT — ПО и облачные сервисы\n"
        "JNJ — медицина и лекарства\n"
        "KO — напитки Coca-Cola\n\n"
        "Нажмите на тикер:",
        reply_markup=kb.safe_stocks)

@router.callback_query(F.data == "stock_popular")
async def stock_popular(callback: CallbackQuery):
    await callback.message.answer(
        "📈 Самые популярные акции\n\n"
        "AAPL — Iphone и устройства\n"
        "NVDA — AI лидер\n"
        "TSLA — электромобили\n"
        "MSFT — ПО и облачные сервисы\n\n"
        "Нажмите на тикер:",
        reply_markup=kb.popular_stocks)




@router.callback_query(F.data == "etfs")
async def cmd_etfs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Mode.waiting_for_ticker)
    await state.update_data(type="etfs")
    await callback.message.answer(
        "🧩 Анализ ETF\n\n"
        "Покажем:\n"
        "• состав фонда\n"
        "• уровень риска\n"
        "• историю доходности\n"
        "• долю соответствующих Шариату активов\n"
        "• итоговый вывод\n\n"
        "Введите тикер фонда\n\n"
        "ИЛИ выберите готовую подборку 👇",
        reply_markup=kb.etf_categories)
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="etfs.opened",
            category="funnel"))


@router.callback_query(F.data == "etf_shariah")
async def etf_shariah(callback: CallbackQuery):
    await callback.message.answer(
        "🕌 ETF, соответствующие Шариату\n\n"
        "SPUS\n"
        "HLAL\n"
        "UMMA\n\n"
        "Нажмите на фонд:",
        reply_markup=kb.shariah_etfs)


@router.callback_query(F.data == "etf_tech")
async def etf_tech(callback: CallbackQuery):
    await callback.message.answer(
        "💻 Технологические ETF\n\n"
        "QQQ\n"
        "VGT\n"
        "HLAL\n\n"
        "Нажмите на фонд:",
        reply_markup=kb.tech_etfs)


@router.callback_query(F.data == "etf_world")
async def etf_world(callback: CallbackQuery):
    await callback.message.answer(
        "🌍 Глобальные ETF\n\n"
        "VT\n"
        "ACWI\n"
        "UMMA\n\n"
        "Нажмите на фонд:",
        reply_markup=kb.world_etfs)


@router.callback_query(F.data == "etf_beginner")
async def etf_beginner(callback: CallbackQuery):
    await callback.message.answer(
        "🛡 ETF для начинающих\n\n"
        "VOO\n"
        "GLD\n"
        "UMMA\n\n"
        "Нажмите на фонд:",
        reply_markup=kb.for_beginners_etfs)



@router.callback_query(F.data == "analyze_again_stocks")
async def analyze_again_stocks(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mode_type = data.get("type")
    await state.set_state(Mode.waiting_for_ticker)
    if mode_type == "stocks":
        await callback.message.answer(
        "📈 Введите тикер компании\n\n"
        "Например:\n"
        "AAPL - Apple,\n"
        "NVDA - NVIDIA,\n"
        "MSFT - Microsoft", reply_markup=kb.stock_categories)


@router.callback_query(F.data == "analyze_again_etfs")
async def analyze_again_etfs(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mode_type = data.get("type")
    await state.set_state(Mode.waiting_for_ticker)
    if mode_type == "etfs":
        await callback.message.answer(
        "🧩 Введите тикер фонда\n\n"
        "Например:\n"
        "• SPUS — исламский аналог S&P 500\n"
        "• HLAL — исламские акции США\n"
        "• SPY — индекс S&P 500\n"
        "• QQQ — крупнейшие технологии США", reply_markup=kb.etf_categories)


async def analyze_ticker(message: Message, state: FSMContext):
    print("STEP 1")
    try:
        mode = await state.get_data()
        print("STEP 2")
        mode_type = mode.get("type")
        print("STEP 3")
        ticker = message.text.strip().upper()
        print("STEP 4")
    except Exception as e:
        print("EARLY CRASH:", repr(e))
        raise
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=message.from_user.id,
            event_name="ticker.entered",
            event_data={
                "ticker": ticker,
                "asset_type": mode_type}))
    if mode_type == "stocks":
        await message.answer("🔍 Анализируем компанию...\n\n"
            "Проверяем:\n"
            "• финансы\n"
            "• уровень риска\n"
            "• соответствие Шариату\n\n"
            "Это займёт несколько секунд.\n")
        start = time.perf_counter()
        data = await get_stock_info(ticker)
        print("get_stock_info:", time.perf_counter() - start)
        if "error" in data:
            await message.answer(data["error"])
            return
        risk_task = asyncio.create_task(get_risk_metrics_cached(ticker))
        screening_task = asyncio.create_task(shariah_screen(data))
        t = time.perf_counter()
        print("shariah_screen:", time.perf_counter() - t)
        t = time.perf_counter()
        screening, risk = await asyncio.gather(screening_task, risk_task)
        print("get_risk_metrics_cached:", time.perf_counter() - t)
        print("RISK =", risk)
        risk_score = risk["risk_score"]
        risk_label = risk["risk_label"]
        pe = data["pe"]
        mc = data["market_cap"]
        insights = []
        if data["growth"]["1Y"] > 30:
            insights.append(("📈", f"Сильный рост за последний год: {data["growth"]["1Y"]}"))
        if data["growth"]["5Y"] > 100:
            insights.append(("🚀", f"Компания более чем удвоилась за 5 лет: {data["growth"]["5Y"]}"))
        if data["growth"]["1Y"] < -20:
            insights.append(("📉", f"Акция переживает сильную просадку{data["growth"]["1Y"]}"))

        if risk_score is None:
            risk_label = "Недостаточно данных"
        elif risk_score >= 80:
            insights.append(("🛡", "Один из самых низких уровней риска"))
        if risk_score <= 50:
            insights.append(("⚠️", "Высокий риск"))
        if risk["drawdown"] < -50:
            insights.append(("📉", "Исторически переживал просадки более 50%"))

        if screening["status"] == "СООТВЕТСТВУЕТ ШАРИАТУ ✅":
            insights.append(("🕌", "Проходит проверку по стандартам Шариата"))
        if screening["status"] == "Скорее соответствует Шариату ⚠️":
            insights.append(("⚠️", "Есть показатели, требующие проверки"))

        if pe and pe < 15:
            insights.append(("💰", "Оценка ниже средней по рынку"))
        if pe and pe > 40:
            insights.append(("🔥", "Инвесторы закладывают высокий рост"))

        if mc > 1_000_000_000_000:
            insights.append(("🏢", "Компания входит в число крупнейших в мире"))
        if mc < 10_000_000_000:
            insights.append(("🌱", "Относительно небольшая компания"))

        if data["debt_to_equity"] < 50:
            insights.append(("🏦", "Низкая долговая нагрузка"))
        if data["debt_to_equity"] > 150:
            insights.append(("⚠️", "Высокая зависимость от долга"))

        if not insights:
            insights.append(("ℹ️", "Нужен дополнительный анализ"))
        random.shuffle(insights)
        selected = insights[:4]
        insight_text = "\n".join(f"{icon} {text}" for icon, text in selected)
        text = f"""
        📊 {data['name']} ({data['ticker']})

    💵 Цена:
    {round(data['price'], 2)}$
            

    🕌 Соответствие Шариату:
    {format_shariah(screening["status"])}


    📊 Риск:  
    {risk_bar(risk_score)}
    {risk_label} ({risk_score}/100)
            
            
    💡 Ключевые факторы
        
    {insight_text}
        
    📈 Рост
     За 1 год: {data['growth']['1Y']}%
     За 5 лет: {data['growth']['5Y']}%
            
    👇 Первый анализ готов.

    Следующий шаг поможет понять,
    стоит ли покупать этот актив именно вам.
            """
        await message.answer(text, reply_markup=kb.after_analysis)
        await state.update_data(
            last_ticker=data["ticker"],
            last_price=data["price"])
        asyncio.create_task(
            AnalyticsService.track_event(
                user_id=message.from_user.id,
                event_name="analysis.completed",
                category="invest",
                event_data={
                    "ticker": ticker,
                    "asset_type": "stock",
                    "risk_score": risk_score,
                    "shariah": screening["status"]}))
        print("ПЕРЕД СОХРАНЕНИЕМ", type(data))
        print("ПЕРЕД СОХРАНЕНИЕМ", type(screening))
        def make_json_safe(obj):
            if isinstance(obj, dict):
                return {k: make_json_safe(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [make_json_safe(v) for v in obj]
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            return obj
        await state.update_data(
            last_ticker=ticker,
            last_price=data["price"],
            last_stock_data=make_json_safe(data),
            last_screening=make_json_safe(screening),
            last_risk_score=risk_score,
            last_risk_label=risk_label)
        return

    if mode_type == "etfs":
        await message.answer("🔍 Анализируем фонд...\n\n"
            "Проверяем состав фонда,\n"
            "уровень риска и соответствие Шариату.")
        start = time.perf_counter()
        data = await get_etf_info(ticker)
        print("ETF INFO-Market:", time.perf_counter() - start)
        if "error" in data:
            await message.answer(data["error"])
            return
        screening, risk_etf = await asyncio.gather(
            shariah_screen_etf_full(ticker, get_etf_holdings),
            calculate_etf_risk(ticker))
        risk = await get_risk_metrics_cached(ticker)
        insights = []
        if screening["halal_percent"] > 90:
            insights.append(("🕌", "Большая часть фонда соответствует Шариату"))
        if screening["covered_percent"] < 60:
            insights.append(("📊", "Покрытие проверки ограничено"))
        if risk["risk_score"] > 80:
            insights.append(("🛡", "ETF относится к более стабильным"))
        if not insights:
            insights.append(("ℹ️", "Нужен дополнительный анализ"))
        selected = insights[:4]
        why_text = "\n".join(f"{icon} {text}" for icon, text in selected)

        text = f"""
    🧩 {data['ticker']}

    💵 Цена: 
    {round(data['price'], 2)}$


    🕌 Соответствие Шариату:
    {format_shariah(screening["status"])}


    📊 Риск: 
    {risk_bar(risk_etf['risk_score'])}
    {risk_etf['risk_label']} ({risk_etf['risk_score']}/100)
            

    💡 Ключевые факторы: 

    {why_text}


    📈 Рост

    За 1 год: {data['growth']['1Y']}%
    За 5 лет: {data['growth']['5Y']}%
            
        👇 Первый анализ готов.

        Следующий шаг поможет понять,
        стоит ли покупать этот актив именно вам.
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
        print("MESSAGE =", message)
        print("FROM USER =", message.from_user)
        asyncio.create_task(
            AnalyticsService.track_event(
                user_id=message.from_user.id,
                event_name="analysis.completed",
                category="invest",
                event_data={"ticker": ticker,
                    "asset_type": "etf"}))
        return


@router.message(Mode.waiting_for_ticker)
async def ticker_handler(message, state):
    await analyze_ticker(message, state)


@router.callback_query(F.data.startswith("quick_"))
async def quick_ticker(callback: CallbackQuery, state: FSMContext):
    print("QUICK CALLBACK FIRED")
    ticker = callback.data.replace("quick_", "")
    print("CALLBACK DATA =", callback.data)
    print(
        "CURRENT FSM =",
        await state.get_data())
    fake_message = callback.message.model_copy(update={"text": ticker})
    try:
        await analyze_ticker(fake_message, state)
    except Exception as e:
        print("QUICK ERROR:", repr(e))
        traceback.print_exc()



@router.callback_query(F.data == "deep_audit")
async def deep_analysis_handler(callback: CallbackQuery,
        state: FSMContext):
    data = await state.get_data()
    mode_type = data.get("type")
    print("DEEP AUDIT STATE: ", data)
    ticker = data.get("last_ticker")
    if not ticker:
        await callback.message.answer("⚠️ Сперва сделайте анализ.")
        return
    asyncio.create_task(
        AnalyticsService.track_event(
            user_id=callback.from_user.id,
            event_name="deep_audit.opened",
            category="funnel",
            event_data={
                "ticker": ticker,
                "asset_type": mode_type}))
    if mode_type == "stocks":
        await callback.message.answer("🧮 Уже делаем детальный анализ...")
        stocks_data = await get_stock_info(ticker)
        if "error" in stocks_data:
            await callback.message.answer(data["error"])
            return
        state_data = await state.get_data()
        stock_data = state_data.get("last_stock_data")
        screening = await shariah_screen(stocks_data)
        if not stock_data:
            await callback.message.answer("Сперва получите анализ актива.")
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
                "соответствует": "✅",
                "на грани": "⚠️",
                "не соответствует": "❌",
                "нейтральный": "➖"}[check["status"]]
            value = (
                f"{check['value']:.2%}"
                if check["value"] is not None
                else "N/A")
            audit_text += (
                f"{icon} {check['name']}\n"
                f"• Оценка: {value}\n"
                f"• Лимит: {check['limit']:.0%}\n"
                f"• Формула: {check['formula']}\n"
                f"• Результат: {check['message']}\n\n")
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
            🔍 Подробный разбор
        📊 {stocks_data['name']} ({stocks_data['ticker']})

        📘 Основные показатели
        • Долг / капитал: {format_percent(stocks_data['debt_to_equity'])}
            Чем ниже - тем лучше
        • Цена / прибыль: {stocks_data['pe']}
            Показывает, как компания ценится на рынке.
            Желательно 20-30 коэффицентов
        • Капитализация: {format_money(stocks_data['market_cap'])}
            Размер компании

        🕌 Проверка по стандартам Шариата

        Статус: {format_shariah(screening["status"])}

        📚 Стандарты:

        • {audit['standard']}

        🏢 Проверка бизнеса

        • {audit['business']['message']}

        📊 Финансовая проверка

        {audit_text}

        🕒 Актуальность данных

        • {freshness_text}

        🧩 Недостающие данные

        • {missing_text}



        📊 Риск

        • Волатильность: {format_percent(vol)}%
            насколько сильно колелблется цена
        • Максимальная просадка: {format_percent(dd)}%
            Самое сильное падение за период
        • Волатильность по сравнению с рынком: {beta}
        • Доходность по отношению с риском: {sharpe}

        • Уровень риска: {risk_label}
        • Оценка риска: {risk_score}/100


        📈 Доходность
        1 день: {stocks_data['growth']['1D']}%
        5 дней: {stocks_data['growth']['5D']}%
        1 месяц: {stocks_data['growth']['1M']}%
        6 месяцев: {stocks_data['growth']['6M']}%
        1 год: {stocks_data['growth']['1Y']}%
        5 лет: {stocks_data['growth']['5Y']}%
        """
        from aiogram.types import BufferedInputFile
        chart = await generate_asset_growth_graph(ticker)
        if chart:
            photo = BufferedInputFile(
                chart.read(),
                filename=f"{ticker}.png")
            await callback.message.answer_photo(photo,
                caption=f"📈 {ticker} Рост цены за 1 год")
        await callback.message.answer(text, reply_markup=kb.after_analysis)

    if mode_type == "etfs":
        await callback.message.answer("🧮 Уже делаем детальный анализ...")
        data = await get_etf_info(ticker)
        if "error" in data:
            await callback.message.answer(data["error"])
            return
        screening = await AnalyticsService.measure(
            user_id=callback.from_user.id,
            event_name="etf.screening",
            coro=shariah_screen_etf_full(ticker, get_etf_holdings))
        risk = await calculate_etf_risk(ticker)
        top_holdings_text = ""
        for item in screening.get("trust_breakdown", [])[:5]:
            status_icon = {
                "СООТВЕТСТВУЕТ ШАРИАТУ ✅": "✅",
                "Скорее соответствует Шариату ⚠️": "⚠️",
                "Нужна дополнительная проверка ⚠️": "⚠️",
                "НЕ СООТВЕТСТВУЕТ ❌": "❌",
                "UNKNOWN": "➖"}.get(item["status"], "➖")
            top_holdings_text += (
                f"{status_icon} {item['ticker']}\n"
                f"• Статус: {item['status']}\n"
                f"• Вес в фонде: {item['weight']:.2%}\n\n")

        text = f"""
            🧩 {data['name']} ({data['ticker']})

        💵 Цена: {round(data['price'], 2)}$

        📦 Данные Фонда
        Активы фонда: {format_money(data['net_assets'])}
        Цена / прибыль: {round(data['pe'], 2)}

        🕌 Проверка фонда на соответствие Шариату

        Статус: {format_shariah(screening["status"])}

        Доля соответствующих активов: {format_percent(screening['halal_percent'])}%
        Покрытие анализа: {format_percent(screening['covered_percent'])}%
        Не удалось проверить: {format_percent(screening.get('unknown_percent', 0))}%

        📚 Покрытие проверки

        • Проверено активов: {format_percent(screening['total_analyzed'])}

        • Покрытие портфеля: {format_percent(screening['covered_percent'])}%

        • Метод: Анализ крупнейших позиций фонда

        📊 Крупнейшие позиции фонда:

        {top_holdings_text}

        📊 Риск

        • Волатильность: {format_percent(risk['volatility'])}%
            Насколько сильно колеблется цена
        • Масимальная просадка: {format_percent(risk['drawdown'])}%
            Самое сильное падение за период
        • Волатильность по сравнению с рынком: {risk['beta']}
        • Доходность по отношению с риском: {risk['sharpe']}

        • Уровень риска: {risk['risk_label']}
        • Оценка риска: {risk['risk_score']}/100


        📈 Рост

        1 день: {data['growth']['1D']}%
        5 дней: {data['growth']['5D']}%
        1 месяц: {data['growth']['1M']}%
        6 месяцев: {data['growth']['6M']}%
        1 год: {data['growth']['1Y']}%
        5 лет: {data['growth']['5Y']}%
        """
        await callback.message.answer(text, reply_markup=kb.after_analysis)
        from aiogram.types import BufferedInputFile
        chart = await generate_asset_growth_graph(ticker)
        if chart:
            photo = BufferedInputFile(
                chart.read(),
                filename=f"{ticker}.png")
            await callback.message.answer_photo(photo,
                caption=f"📈 {ticker} Рост цены за 1 год")
        data_state = await state.get_data()
        ticker = data_state["last_ticker"]
        asyncio.create_task(
            AnalyticsService.track_event(
                user_id=callback.message.from_user.id,
                event_name="etf.analyzed",
                category="invest",
                event_data={"ticker": ticker}))
        return