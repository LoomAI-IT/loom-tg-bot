from aiogram.fsm.state import StatesGroup, State

class PersonalProfileStates(StatesGroup):
    personal_profile = State()
    faq = State()
    support = State()