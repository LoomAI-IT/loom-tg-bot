from aiogram.fsm.state import StatesGroup, State


class ModerationPublicationStates(StatesGroup):
    moderation_list = State()
    reject_comment = State()
    edit_preview = State()

    edit_text_menu = State()
    edit_image_menu = State()

    edit_text = State()
    upload_image = State()

    # Состояния подтверждения нового изображения
    new_image_confirm = State()

    # Состояния объединения изображений
    combine_images_choice = State()
    combine_images_upload = State()
    combine_images_prompt = State()

    social_network_select = State()

    # Алерты
    text_too_long_alert = State()

    publication_success = State()