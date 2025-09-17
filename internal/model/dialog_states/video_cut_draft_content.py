# internal/model/dialog_states/video_cut_draft_content.py
from aiogram.fsm.state import StatesGroup, State

class VideoCutDraftContentStates(StatesGroup):
    video_drafts_list = State()
    video_draft_detail = State()
    edit_video_draft = State()