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
            kontur_account_client: interface.IKonturAccountClient,
            kontur_employee_client: interface.IKonturEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_account_client = kontur_account_client
        self.kontur_employee_client = kontur_employee_client

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
                dialog_manager.dialog_data["user_agreement_accepted"] = True

                self.logger.info("Пользователь принял пользовательское соглашение")

                # Переходим к следующему окну
                await dialog_manager.switch_to(model.AuthStates.privacy_policy)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Произошла ошибка. Попробуйте снова.", show_alert=True)
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
                # Сохраняем принятие
                dialog_manager.dialog_data["privacy_policy_accepted"] = True

                self.logger.info("Пользователь принял политику конфиденциальности")

                # Переходим к следующему окну
                await dialog_manager.switch_to(model.AuthStates.data_processing)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Произошла ошибка. Попробуйте снова.", show_alert=True)
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
                chat_id = callback.message.chat.id

                # Сохраняем принятие
                dialog_manager.dialog_data["data_processing_accepted"] = True

                # Регистрируем пользователя
                authorized_data = await self.kontur_account_client.register_from_tg(
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

                self.logger.info("Пользователь завершил процесс авторизации")

                # Проверяем доступ к организации
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    authorized_data.account_id
                )

                if employee:
                    await self.state_repo.change_user_state(
                        state.id,
                        organization_id=employee.organization_id
                    )

                    await dialog_manager.start(
                        model.MainMenuStates.main_menu,
                        mode=StartMode.RESET_STACK
                    )
                else:
                    # Если нет доступа - переходим к окну отказа
                    await dialog_manager.switch_to(model.AuthStates.access_denied)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
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
                await callback.answer(
                    "Обратитесь к администратору для получения доступа.",
                    show_alert=True
                )

                # Завершаем диалог
                await dialog_manager.done()
                await dialog_manager.reset_stack()

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
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
