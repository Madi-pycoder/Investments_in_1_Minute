from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

maind = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="📈 Analyze Stocks",
            callback_data="stocks"),
        InlineKeyboardButton(
            text="🧩 Analyze ETFs",
            callback_data="etfs")],
        [InlineKeyboardButton(
            text="💼 My Portfolio",
            callback_data="portfolio_hub")]])


after_analysis = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🔄 Analyze Another', callback_data='analyze_again')],
    [InlineKeyboardButton(text='🏠 Main menu', callback_data='main_menu')],
    [InlineKeyboardButton(text='📊 Add to Portfolio', callback_data='buy')],
    [InlineKeyboardButton(text='🧮 Detailed Analysis', callback_data='deep_audit')]])


portfolio_dashboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Show Portfolio",
            callback_data="portfolio")],
        [InlineKeyboardButton(
            text="🧠 AI Analysis",
            callback_data="financial_brain"),
        InlineKeyboardButton(
            text="⚡ Quick Fix",
            callback_data="goal_fix")],
        [InlineKeyboardButton(
            text="🎯 My Goals",
            callback_data="goal_view"),
        InlineKeyboardButton(
            text="🚀 Auto Invest",
            callback_data="auto_invest")],
        [InlineKeyboardButton(
            text="🧮 What If",
            callback_data="what_if")],
        [InlineKeyboardButton(
            text="🔄 Switch Portfolio",
            callback_data="portfolio_hub"),
        InlineKeyboardButton(
            text="➕ Add Goal",
            callback_data="goal_settings")],
        [InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu")]])


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


goal_name_quiz = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="🏠 House",
            callback_data="goal_house"),
        InlineKeyboardButton(
            text="🚗 Car",
            callback_data="goal_car")],
        [InlineKeyboardButton(
            text="💰 Passive Income",
            callback_data="goal_passive_income"),
        InlineKeyboardButton(
            text="✈️ Travel",
            callback_data="goal_travel")],
        [InlineKeyboardButton(
            text="🧠 Custom",
            callback_data="goal_custom")]])



goal_amount_quiz = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="$5K",
            callback_data="amount_5000"),
        InlineKeyboardButton(
            text="$10K",
            callback_data="amount_10000")],
        [InlineKeyboardButton(
            text="$50K",
            callback_data="amount_50000"),
        InlineKeyboardButton(
            text="🧠 Custom",
            callback_data="amount_custom")]])



goal_timeline = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="1Y",
            callback_data="timeline_1"),
        InlineKeyboardButton(
            text="3Y",
            callback_data="timeline_3")],
        [InlineKeyboardButton(
            text="5Y",
            callback_data="timeline_5"),
            InlineKeyboardButton(
            text="Custom",
            callback_data="timeline_custom")]])



goal_compliance = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="🕌 Shariah",
            callback_data="compliance_shariah")],
        [InlineKeyboardButton(
            text="📈 Conventional",
            callback_data="compliance_conventional")]])

add_goal = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Add Goal", callback_data="goal_settings")]])

create_demo = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Create Portfolio",callback_data="create_demo")]])

login_demo = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💼 My Portfolio",callback_data="portfolio_hub")]])

after_show_portfolio = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="🧠 AI Analysis",
            callback_data="financial_brain"),
            InlineKeyboardButton(
            text="⚡ Quick Fix",
            callback_data="goal_fix")],
        [InlineKeyboardButton(
            text="🎯 My Goals",
            callback_data="goal_view"),
        InlineKeyboardButton(
            text="🚀 Auto Invest",
            callback_data="auto_invest")],
        [InlineKeyboardButton(
            text="🧮 What If",
            callback_data="what_if")],
        [InlineKeyboardButton(
            text="🔄 Switch Portfolio",
            callback_data="portfolio_hub"),
        InlineKeyboardButton(
            text="➕ Add Goal",
            callback_data="goal_settings")
        ],
        [InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu")]])