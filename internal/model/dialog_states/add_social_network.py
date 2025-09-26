from aiogram.fsm.state import StatesGroup, State

class AddSocialNetworkStates(StatesGroup):
    select_network = State()

    telegram_main = State()        # Новое состояние - главное окно telegram
    telegram_connect = State()     # Новое состояние - подключение канала
    telegram_edit = State()

    vkontakte_setup = State()
    youtube_setup = State()
    telegram_change_username = State()
    instagram_setup = State()