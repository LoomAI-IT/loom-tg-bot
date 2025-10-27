from aiogram.fsm.state import StatesGroup, State


class PublicationDraftStates(StatesGroup):
    # Основное окно - список черновиков  
    publication_list = State()
    
    # Окно превью с кнопками действий
    edit_preview = State()
    
    # Редактирование текста
    edit_text_menu = State()      
    regenerate_text = State()
    edit_title = State()
    edit_description = State()
    edit_content = State()
    
    # Редактирование изображения
    edit_image_menu = State()
    generate_image = State()
    upload_image = State()
    
    # Настройки публикации
    edit_tags = State()
    social_network_select = State()


__all__ = ["PublicationDraftStates"]