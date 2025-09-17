# internal/model/dialog_states/generate_publication.py
from aiogram.fsm.state import StatesGroup, State

class GeneratePublicationStates(StatesGroup):
    select_category = State()
    input_text = State()
    choose_image_option = State()
    image_generation = State()
    preview = State()
    select_publish_location = State()