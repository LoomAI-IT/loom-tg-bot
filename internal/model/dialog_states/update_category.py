from aiogram.fsm.state import StatesGroup, State


class UpdateCategoryStates(StatesGroup):
    select_category = State()
    update_category = State()
    category_updated = State()