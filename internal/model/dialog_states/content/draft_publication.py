from aiogram.fsm.state import StatesGroup, State


class DraftPublicationStates(StatesGroup):
    draft_list = State()
    edit_preview = State()

    edit_text_menu = State()
    edit_image_menu = State()

    edit_text = State()
    edit_image_input = State()
    upload_image = State()

    # Состояния генерации изображений
    image_generation_mode_select = State()
    reference_image_generation = State()
    reference_image_upload = State()

    # Состояния подтверждения нового изображения
    new_image_confirm = State()

    # Состояния объединения изображений
    combine_images_choice = State()
    combine_images_upload = State()
    combine_images_prompt = State()

    social_network_select = State()

    # Алерты
    text_too_long_alert = State()