from aiogram.fsm.state import StatesGroup, State


class ModerationPublicationStates(StatesGroup):
    moderation_list = State()
    reject_comment = State()
    edit_preview = State()

    edit_text_menu = State()
    edit_image_menu = State()

    edit_text = State()
    upload_image = State()

    social_network_select = State()