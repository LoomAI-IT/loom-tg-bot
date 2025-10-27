
from aiogram.fsm.state import State, StatesGroup


class GeneratePublicationStates(StatesGroup):
    # Основные состояния
    select_category = State()
    input_text = State()
    generation = State()
    preview = State()

    # Состояния редактирования текста
    edit_text_menu = State()
    regenerate_text = State()
    edit_text = State()

    # Состояния управления изображением
    image_menu = State()
    generate_image = State()
    new_image_confirm = State()
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