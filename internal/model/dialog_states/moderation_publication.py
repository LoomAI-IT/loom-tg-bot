from aiogram.fsm.state import StatesGroup, State


class ModerationPublicationStates(StatesGroup):
    moderation_list = State()
    publication_review = State()
    reject_comment = State()

    # Состояния редактирования (как в GeneratePublication)
    edit_text_menu = State()
    edit_title = State()
    edit_tags = State()
    edit_content = State()

    # Состояния для изображения
    edit_image_menu = State()
    generate_image = State()
    upload_image = State()