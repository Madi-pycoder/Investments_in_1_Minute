from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

maind = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Stocks', callback_data='stocks')],
    [InlineKeyboardButton(text='ETFs', callback_data='etfs')],
    [InlineKeyboardButton(text='Create Demo-Portfolio', callback_data='create demo')],
    [InlineKeyboardButton(text='Log in old Demo-Portfolio', callback_data='login demo')],
])
resize_keyboard=True
input_field_placeholder="From what will we start?"