from aiogram.fsm.state import StatesGroup, State


class VideoCutsDraftStates(StatesGroup):
    """Стейты для диалога управления черновиками видеонарезок"""

    # Основное окно со списком черновиков и отображением видео
    video_cut_list = State()

    # Окно редактирования с превью
    edit_preview = State()

    # Окна редактирования конкретных полей
    edit_title = State()
    edit_description = State()
    edit_tags = State()

    # Окно настроек публикации
    social_network_select = State()