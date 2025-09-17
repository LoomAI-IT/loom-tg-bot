from aiogram.fsm.state import StatesGroup, State

class ContentMenuStates(StatesGroup):
    content_menu = State()
    select_content_type = State()
    select_drafts_type = State()
    select_moderation_type = State()