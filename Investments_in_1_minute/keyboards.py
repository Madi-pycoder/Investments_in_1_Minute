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
            InlineKeyboardButton(text="🧠 Explain My Portfolio", callback_data="explain_portfolio"),
        ],
        [
            InlineKeyboardButton(text="⚖️ Rebalance in 1-Tap", callback_data="rebalance_now"),
        ],
    ]
)