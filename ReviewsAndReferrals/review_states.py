from aiogram.fsm.state import StatesGroup, State

class ReviewStates(StatesGroup):
    waiting_rating = State()
    waiting_text = State()