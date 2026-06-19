from aiogram.fsm.state import State, StatesGroup

class ProfileSetup(StatesGroup):
    income = State()
    budget = State()
    risk = State()
    confirm_budget = State()