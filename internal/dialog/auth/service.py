import uuid
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


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

    async def accept_user_agreement(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AuthDialogService.accept_user_agreement",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало принятия пользовательского соглашения")

                dialog_manager.dialog_data["user_agreement_accepted"] = True

                # Переходим к следующему окну
                await dialog_manager.switch_to(model.AuthStates.privacy_policy)

                self.logger.info("Завершение принятия пользовательского соглашения")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def accept_privacy_policy(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AuthDialogService.accept_privacy_policy",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало принятия политики конфиденциальности")

                # Сохраняем принятие
                dialog_manager.dialog_data["privacy_policy_accepted"] = True

                # Переходим к следующему окну
                await dialog_manager.switch_to(model.AuthStates.data_processing)

                self.logger.info("Завершение принятия политики конфиденциальности")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def accept_data_processing(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager,
    ) -> None:
        with self.tracer.start_as_current_span(
                "AuthDialogService.accept_data_processing",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало принятия согласия на обработку данных")

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
                    # Если нет доступа - переходим к окну отказа
                    await dialog_manager.switch_to(model.AuthStates.access_denied)

                self.logger.info("Завершение принятия согласия на обработку данных")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def handle_access_denied(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AuthDialogService.handle_access_denied",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки отказа в доступе")

                await callback.answer()

                # Завершаем диалог
                await dialog_manager.done()
                await dialog_manager.reset_stack()

                self.logger.info("Завершение обработки отказа в доступе")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            chat_id = None

        state = (await self.state_repo.state_by_id(chat_id))[0]
        return state
