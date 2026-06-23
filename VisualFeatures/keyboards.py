maind = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="📈 Акции",
            callback_data="stocks"),
        InlineKeyboardButton(
            text="🧩 ETF",
            callback_data="etfs")],
        [InlineKeyboardButton(
            text="💼 Мой Портфель",
            callback_data="portfolio_hub")]])


after_analysis = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Купить",
            callback_data="buy")],
        [InlineKeyboardButton(
            text="🧮 Полная проверка",
            callback_data="deep_audit")],
        [InlineKeyboardButton(
            text="📈 Новый анализ акции",
            callback_data="analyze_again_stocks")],
        [InlineKeyboardButton(
            text="🧩 Новый анализ фонда",
            callback_data="analyze_again_etfs")],
        [InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="main_menu")]])


portfolio_dashboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Портфель",
            callback_data="portfolio")],
        [InlineKeyboardButton(
            text="🧠 Что улучшить?",
            callback_data="financial_brain"),
        InlineKeyboardButton(
            text="⚡ Быстро исправить",
            callback_data="goal_fix")],
        [InlineKeyboardButton(
            text="🎯 Цели",
            callback_data="goal_view"),
        InlineKeyboardButton(
            text="🚀 Авто-Инвестиции",
            callback_data="auto_invest")],
        [InlineKeyboardButton(
            text="🧮 Сценарии",
            callback_data="what_if")],
        [InlineKeyboardButton(
            text="🔄 Мои Портфели",
            callback_data="portfolio_hub"),
        InlineKeyboardButton(
            text="➕ Добавить Цель",
            callback_data="goal_settings")],
        [InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="main_menu")]])




popular_etfs = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="SPUS",
            callback_data="quick_SPUS"),
        InlineKeyboardButton(
            text="HLAL",
            callback_data="quick_HLAL")],
        [InlineKeyboardButton(
            text="SPY",
            callback_data="quick_SPY"),
        InlineKeyboardButton(
            text="QQQ",
            callback_data="quick_QQQ")]])


stock_categories = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Потенциал роста",
            callback_data="stock_growth")],
        [InlineKeyboardButton(
            text="🕌 Акции, соответствующие Шариату",
            callback_data="stock_shariah")],
        [InlineKeyboardButton(
            text="🛡 Низкий риск",
            callback_data="stock_safe")],
        [InlineKeyboardButton(
            text="📈 Популярные",
            callback_data="stock_popular")]])

growth_stocks = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="NVDA",
            callback_data="quick_NVDA"),
        InlineKeyboardButton(
            text="AMD",
            callback_data="quick_AMD")],
        [InlineKeyboardButton(
            text="TSLA",
            callback_data="quick_TSLA"),
        InlineKeyboardButton(
            text="META",
            callback_data="quick_META")]])

shariah_stocks = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="AAPL",
            callback_data="quick_AAPL"),
        InlineKeyboardButton(
            text="GOOGL",
            callback_data="quick_GOOGL")],
        [InlineKeyboardButton(
            text="TSM",
            callback_data="quick_TSM"),
        InlineKeyboardButton(
            text="NVDA",
            callback_data="quick_NVDA")]])

safe_stocks = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="BRK.B",
            callback_data="quick_BRK.B"),
        InlineKeyboardButton(
            text="MSFT",
            callback_data="quick_MSFT")],
        [InlineKeyboardButton(
            text="JNJ",
            callback_data="quick_JNJ"),
        InlineKeyboardButton(
            text="KO",
            callback_data="quick_KO")]])

popular_stocks = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="AAPL",
            callback_data="quick_AAPL"),
        InlineKeyboardButton(
            text="NVDA",
            callback_data="quick_NVDA")],
        [InlineKeyboardButton(
            text="TSLA",
            callback_data="quick_TSLA"),
        InlineKeyboardButton(
            text="MSFT",
            callback_data="quick_MSFT")]])




etf_categories = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="🕌 ETF, соответствующие Шариату",
            callback_data="etf_shariah")],
        [InlineKeyboardButton(
            text="💻 Технологии",
            callback_data="etf_tech")],
        [InlineKeyboardButton(
            text="🌍 Мировой рынок",
            callback_data="etf_world")],
        [InlineKeyboardButton(
            text="🛡 Для начинающих",
            callback_data="etf_beginner")]])

shariah_etfs = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="SPUS",
            callback_data="quick_SPUS")],
        [InlineKeyboardButton(
            text="HLAL",
            callback_data="quick_HLAL")],
        [InlineKeyboardButton(
            text="UMMA",
            callback_data="quick_UMMA")]])

tech_etfs = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="VGT",
            callback_data="quick_VGT")],
        [InlineKeyboardButton(
            text="HLAL",
            callback_data="quick_HLAL")],
        [InlineKeyboardButton(
            text="QQQ",
            callback_data="quick_QQQ")]])

for_beginners_etfs = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="VOO",
            callback_data="quick_VOO")],
        [InlineKeyboardButton(
            text="GLD",
            callback_data="quick_GLD")],
        [InlineKeyboardButton(
            text="UMMA",
            callback_data="quick_UMMA")]])

world_etfs = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="VT",
            callback_data="quick_VT")],
        [InlineKeyboardButton(
            text="ACWI",
            callback_data="quick_ACWI")],
        [InlineKeyboardButton(
            text="UMMA",
            callback_data="quick_UMMA")]])


goal_name_quiz = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="🏠 Квартира",
            callback_data="goal_Квартира"),
        InlineKeyboardButton(
            text="🚗 Машина",
            callback_data="goal_Машина")],
        [InlineKeyboardButton(
            text="💰 Пассивный доход",
            callback_data="goal_Пассивный Доход"),
        InlineKeyboardButton(
            text="✈️ Путешествие",
            callback_data="goal_Путешествие")],
        [InlineKeyboardButton(
            text="🧠 Своя цель",
            callback_data="goal_custom")]])



goal_amount_quiz = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="$5 000",
            callback_data="amount_5000"),
        InlineKeyboardButton(
            text="$10 000",
            callback_data="amount_10000")],
        [InlineKeyboardButton(
            text="$50 000",
            callback_data="amount_50000"),
        InlineKeyboardButton(
            text="🧠 Своя цель",
            callback_data="amount_custom")]])



goal_timeline = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="1 год",
            callback_data="timeline_1"),
        InlineKeyboardButton(
            text="3 года",
            callback_data="timeline_3")],
        [InlineKeyboardButton(
            text="5 лет",
            callback_data="timeline_5"),
            InlineKeyboardButton(
            text="Свой срок",
            callback_data="timeline_custom")]])



goal_compliance = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="🕌 Только соответствующие",
            callback_data="compliance_shariah")],
        [InlineKeyboardButton(
            text="📈 Любые инвестиции",
            callback_data="compliance_conventional")]])

add_goal = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Добавить цель",
            callback_data="goal_settings")]])

create_demo = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Создать портфель",
            callback_data="create_demo")]])

login_demo = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💼 Мой портфель",
            callback_data="portfolio_hub")]])

after_show_portfolio = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="🧠 Что улучшить?",
            callback_data="financial_brain"),
            InlineKeyboardButton(
                text="⚡ Быстро исправить",
                callback_data="goal_fix")],
        [InlineKeyboardButton(
            text="🎯 Цели",
            callback_data="goal_view"),
            InlineKeyboardButton(
                text="🚀 Авто-Инвестиции",
                callback_data="auto_invest")],
        [InlineKeyboardButton(
            text="🧮 Сценарии",
            callback_data="what_if")],
        [InlineKeyboardButton(
            text="🔄 Мои Портфели",
            callback_data="portfolio_hub"),
            InlineKeyboardButton(
                text="➕ Добавить Цель",
                callback_data="goal_settings")],
        [InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="main_menu")]])
