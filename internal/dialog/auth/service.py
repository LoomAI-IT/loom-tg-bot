import uuid
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class AuthService(interface.IAuthService):

    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_account_client: interface.ILoomAccountClient,
            loom_employee_client: interface.ILoomEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_account_client = loom_account_client
        self.loom_employee_client = loom_employee_client

    @auto_log()
    @traced_method()
    async def accept_user_agreement(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.dialog_data["user_agreement_accepted"] = True
        await dialog_manager.switch_to(model.AuthStates.privacy_policy)

    @auto_log()
    @traced_method()
    async def accept_privacy_policy(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.dialog_data["privacy_policy_accepted"] = True
        await dialog_manager.switch_to(model.AuthStates.data_processing)

    @auto_log()
    @traced_method()
    async def accept_data_processing(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager,
    ) -> None:
        chat_id = callback.message.chat.id

        # Сохраняем принятие
        dialog_manager.dialog_data["data_processing_accepted"] = True

        # Регистрируем пользователя
        authorized_data = await self.loom_account_client.register_from_tg(
            uuid.uuid4().hex,
            uuid.uuid4().hex,
        )

        state = (await self.state_repo.state_by_id(chat_id))[0]

        # Обновляем состояние пользователя
        await self.state_repo.change_user_state(
            state.id,
            account_id=authorized_data.account_id,
            access_token=authorized_data.access_token,
            refresh_token=authorized_data.refresh_token
        )

        # Проверяем доступ к организации
        employee = await self.loom_employee_client.get_employee_by_account_id(
            authorized_data.account_id
        )

        if employee:
            self.logger.info("Сотрудник найден, обновляем organization_id")
            await self.state_repo.change_user_state(
                state.id,
                organization_id=employee.organization_id
            )

            await dialog_manager.start(
                model.MainMenuStates.main_menu,
                mode=StartMode.RESET_STACK
            )
        else:
            self.logger.info("Сотрудник не найден, переход к access_denied")
            await dialog_manager.switch_to(model.AuthStates.access_denied)

    @auto_log()
    @traced_method()
    async def handle_access_denied(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        await callback.answer()

        # Завершаем диалог
        await dialog_manager.done()
        await dialog_manager.reset_stack()

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            chat_id = None

        state = (await self.state_repo.state_by_id(chat_id))[0]
        return state
