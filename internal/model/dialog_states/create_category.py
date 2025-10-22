from aiogram.fsm.state import StatesGroup, State


class CreateCategoryStates(StatesGroup):
    create_category = State()
    category_created = State()