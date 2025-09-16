from aiogram.fsm.state import StatesGroup, State


class AuthStates(StatesGroup):
    user_agreement = State()
    privacy_policy = State()
    data_processing = State()
    welcome = State()
    access_denied = State()