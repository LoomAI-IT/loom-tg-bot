from aiogram.fsm.state import StatesGroup, State


class IntroStates(StatesGroup):
    welcome = State()
    user_agreement = State()
    privacy_policy = State()
    data_processing = State()
    intro = State()
    create_organization = State()
    join_to_organization = State()