# internal/model/dialog_states/publication_draft_content.py
from aiogram.fsm.state import StatesGroup, State

class PublicationDraftContentStates(StatesGroup):
    drafts_list = State()
    draft_detail = State()
    edit_draft = State()