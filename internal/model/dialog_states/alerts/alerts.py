from aiogram.fsm.state import StatesGroup, State

class AlertsStates(StatesGroup):
    video_generated_alert = State()
    publication_approved_alert = State()
    publication_rejected_alert = State()
