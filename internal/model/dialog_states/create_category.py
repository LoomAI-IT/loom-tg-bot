from aiogram.fsm.state import StatesGroup, State


class CreateCategoryStates(StatesGroup):
    create_category = State()
    confirm_cancel = State()
    category_created = State()