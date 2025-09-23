from aiogram.fsm.state import StatesGroup, State

class GenerateVideoCutStates(StatesGroup):
    input_youtube_link = State()
    video_generated_alert = State()
