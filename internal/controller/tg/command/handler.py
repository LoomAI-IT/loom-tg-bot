import traceback

from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, StatusCode

from internal import model, interface


class CommandController(interface.ICommandController):

    def __init__(
            self,
            tel: interface.ITelemetry,
            state_service: interface.IStateService
    ):
        self.logger = tel.logger()
        self.tracer = tel.tracer()
        self.state_service = state_service

    async def start_handler(
            self,
            message: Message,
            dialog_manager: DialogManager,
            # user_state: model.UserState
    ):
        with self.tracer.start_as_current_span(
                "CommandController.start_handler",
                kind=SpanKind.INTERNAL
        ) as span:
            try:

                tg_chat_id = dialog_manager.event.chat.id

                user_state = await self.state_service.state_by_id(tg_chat_id)
                if not user_state:
                    await self.state_service.create_state(tg_chat_id)
                    user_state = await self.state_service.state_by_id(tg_chat_id)
                user_state = user_state[0]

                if user_state.organization_id == 0 and user_state.account_id == 0:
                    await dialog_manager.start(
                        model.AuthStates.user_agreement,
                        mode=StartMode.RESET_STACK
                    )
                elif user_state.organization_id == 0 and user_state.account_id != 0:
                    await dialog_manager.start(
                        model.AuthStates.access_denied,
                        mode=StartMode.RESET_STACK
                    )
                else:
                    await dialog_manager.start(
                        model.MainMenuStates.main_menu,
                        mode=StartMode.RESET_STACK
                    )

                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                self.logger.error("Failed to start command handler", {"traceback": traceback.format_exc()})
                raise err