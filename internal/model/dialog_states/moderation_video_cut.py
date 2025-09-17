# internal/model/dialog_states/moderation_video_cut.py
from aiogram.fsm.state import StatesGroup, State

class ModerationVideoCutStates(StatesGroup):
    video_moderation_list = State()
    video_review = State()
    reject_comment = State()