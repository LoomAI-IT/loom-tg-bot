from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.trace_wrapper import traced_method


class MainMenuGetter(interface.IMainMenuGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

        self.state_repo = state_repo

    @traced_method()
    async def get_main_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_state(dialog_manager)
        user = dialog_manager.event.from_user

        show_error_recovery = bool(
            state.show_error_recovery) if state.show_error_recovery is not None else False

        data = {
            "name": user.first_name or "Пользователь",
            "show_error_recovery": show_error_recovery,
            "voice_transcribe": dialog_manager.dialog_data.get("voice_transcribe", False),

            "has_void_input_text": dialog_manager.dialog_data.get("has_void_input_text", False),
            "has_small_input_text": dialog_manager.dialog_data.get("has_small_input_text", False),
            "has_big_input_text": dialog_manager.dialog_data.get("has_big_input_text", False),
            # Voice input error flags
            "has_invalid_content_type": dialog_manager.dialog_data.get("has_invalid_content_type", False),
            "has_long_voice_duration": dialog_manager.dialog_data.get("has_long_voice_duration", False),
            "has_empty_voice_text": dialog_manager.dialog_data.get("has_empty_voice_text", False),
            "has_invalid_youtube_url": dialog_manager.dialog_data.get("has_invalid_youtube_url", False),
        }

        await self.state_repo.change_user_state(
            state_id=state.id,
            show_error_recovery=False
        )

        return data

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]
