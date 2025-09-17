# internal/model/dialog_states/moderation_publication.py
from aiogram.fsm.state import StatesGroup, State

class ModerationPublicationStates(StatesGroup):
    moderation_list = State()
    publication_review = State()
    reject_comment = State()