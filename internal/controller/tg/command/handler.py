import traceback

from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, StatusCode

from internal import model, interface
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class CommandController(interface.ICommandController):

    def __init__(
            self,
            tel: interface.ITelemetry,
            state_service: interface.IStateService
    ):
        self.logger = tel.logger()
        self.tracer = tel.tracer()
        self.state_service = state_service

    @auto_log()
    @traced_method()
    async def start_handler(
            self,
            message: Message,
            dialog_manager: DialogManager
    ):
        await dialog_manager.reset_stack()

        tg_chat_id = dialog_manager.event.chat.id

        user_state = await self.state_service.state_by_id(tg_chat_id)
        if not user_state:
            tg_username = message.from_user.username if message.from_user.username else "отсутвует username"
            await self.state_service.create_state(tg_chat_id, tg_username)
            user_state = await self.state_service.state_by_id(tg_chat_id)

        user_state = user_state[0]

        await self.state_service.change_user_state(
            state_id=user_state.id,
            show_error_recovery=False
        )

        if user_state.organization_id == 0 and user_state.account_id == 0:
            await dialog_manager.start(
                model.IntroStates.user_agreement,
                mode=StartMode.RESET_STACK
            )
        elif user_state.organization_id == 0 and user_state.account_id != 0:
            await dialog_manager.start(
                model.IntroStates.access_denied,
                mode=StartMode.RESET_STACK
            )
        else:
            await dialog_manager.start(
                model.MainMenuStates.main_menu,
                mode=StartMode.RESET_STACK
            )
