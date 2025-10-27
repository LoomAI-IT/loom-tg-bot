from aiogram.fsm.state import StatesGroup, State

class VideoCutModerationStates(StatesGroup):
    moderation_list = State()

    reject_comment = State()

    edit_preview = State()

    edit_title = State()
    edit_description = State()
    edit_tags = State()

    social_network_select = State()