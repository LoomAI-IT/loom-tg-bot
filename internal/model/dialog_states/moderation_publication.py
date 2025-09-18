from aiogram.fsm.state import StatesGroup, State


class ModerationPublicationStates(StatesGroup):
    moderation_list = State()
    reject_comment = State()
    edit_preview = State()

    edit_text_menu = State()
    regenerate_text = State()

    edit_title = State()
    edit_tags = State()
    edit_content = State()
    edit_image_menu = State()
    generate_image = State()
    upload_image = State()