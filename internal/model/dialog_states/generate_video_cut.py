# internal/model/dialog_states/generate_video_cut.py
from aiogram.fsm.state import StatesGroup, State

class GenerateVideoCutStates(StatesGroup):
    input_youtube_link = State()
    processing = State()
    video_preview = State()
    edit_video_details = State()
    select_platforms = State()