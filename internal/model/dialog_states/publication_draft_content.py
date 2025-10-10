from aiogram.fsm.state import StatesGroup, State


class PublicationDraftStates(StatesGroup):
    # Основное окно - список черновиков  
    publication_list = State()
    
    # Окно превью с кнопками действий
    edit_preview = State()
    
    # Редактирование текста
    edit_text_menu = State()
    edit_text = State()
    
    # Редактирование изображения
    edit_image_menu = State()
    upload_image = State()
    
    # Настройки публикации
    social_network_select = State()
    publication_success = State()


__all__ = ["PublicationDraftStates"]