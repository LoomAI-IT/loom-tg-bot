from aiogram.fsm.state import StatesGroup, State

class MainMenuStates(StatesGroup):
    personal_profile = State()
    faq = State()
    support = State()