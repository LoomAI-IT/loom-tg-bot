from aiogram.fsm.state import StatesGroup, State

class AlertsStates(StatesGroup):
    video_generated_alert = State()
