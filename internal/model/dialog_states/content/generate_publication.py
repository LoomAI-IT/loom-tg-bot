
from aiogram.fsm.state import State, StatesGroup


class GeneratePublicationStates(StatesGroup):
    # Основные состояния
    select_category = State()
    generate_text_prompt_input = State()
    generation = State()
    preview = State()

    # Состояния редактирования текста
    edit_text_menu = State()
    regenerate_text = State()
    edit_text = State()

    # Состояния управления изображением
    image_menu = State()
    edit_image_input = State()
    generate_image = State()
    generate_image_mode_select = State()
    reference_generate_image = State()
    reference_image_upload = State()
    new_image_confirm = State()
    generate_image_error = State()
    upload_image = State()

    # Состояния объединения изображений
    combine_images_choice = State()
    combine_images_upload = State()
    combine_images_prompt = State()

    # Публикация
    social_network_select = State()

    # Алерты
    text_too_long_alert = State()

    publication_success = State()