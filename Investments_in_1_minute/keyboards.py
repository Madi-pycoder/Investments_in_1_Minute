from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

maind = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Stocks', callback_data='stocks')],
    [InlineKeyboardButton(text='ETFs', callback_data='etfs')],
    [InlineKeyboardButton(text='Portfolio', callback_data='portfolio')],
    [InlineKeyboardButton(text='Create Demo-Portfolio', callback_data='create demo')],
    [InlineKeyboardButton(text='Log in old Demo-Portfolio', callback_data='login demo')],
])
resize_keyboard=True
input_field_placeholder="From what will we start?"



after_analysis = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Analyze again', callback_data='analyze_again')],
    [InlineKeyboardButton(text='Main menu', callback_data='main_menu')],
    [InlineKeyboardButton(text='Sell', callback_data='sell')],
    [InlineKeyboardButton(text='Buy', callback_data='buy')],
])



after_portfolio_action = InlineKeyboardMarkup(
    inline_keyboard=[

        [
            InlineKeyboardButton(text="📊 Diagnosis", callback_data="explain_portfolio"),
            InlineKeyboardButton(text="🧮 What-If", callback_data="what_if"),
        ],


        [
            InlineKeyboardButton(text="🤖 Auto-Invest", callback_data="auto_invest"),
            InlineKeyboardButton(text="🎯 Fix Goal", callback_data="goal_fix"),
        ],


        [
            InlineKeyboardButton(text="⚖️ Smart Rebalance", callback_data="rebalance_now"),
            InlineKeyboardButton(text="🕌 Shariah", callback_data="rebalance_shariah"),
        ],


        [
            InlineKeyboardButton(text="📈 Goals", callback_data="goal_settings"),
            InlineKeyboardButton(text="⚡ Run Now", callback_data="run_auto_now"),
            InlineKeyboardButton(text="🧠 Financial Brain", callback_data="financial_brain"),
        ]
    ]
)
