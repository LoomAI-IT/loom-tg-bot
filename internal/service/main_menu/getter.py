from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class MainMenuGetter(interface.IMainMenuGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

        self.state_repo = state_repo

    async def get_main_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "MainMenuGetter.get_main_menu_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)

                vizard_alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(
                    state_id=state.id,
                )
                if vizard_alerts:
                    await dialog_manager.start(
                        model.GenerateVideoCutStates.video_generated_alert,
                        mode=StartMode.RESET_STACK
                    )
                    await self.state_repo.delete_state_by_tg_chat_id(state.id)
                    raise common.AiogramDialogGetterSpecialError("Vizard alert")


                user = dialog_manager.event.from_user

                data = {
                    "name": user.first_name or "Пользователь",
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

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
