import uuid
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class AuthDialogService(interface.IAuthDialogService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            domain: str,
            kontur_account_client: interface.IKonturAccountClient,
            kontur_organization_client: interface.IKonturOrganizationClient,
            kontur_employee_client: interface.IKonturEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.domain = domain
        self.kontur_account_client = kontur_account_client
        self.kontur_organization_client = kontur_organization_client
        self.kontur_employee_client = kontur_employee_client

    async def accept_user_agreement(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AuthDialogHandler.accept_user_agreement",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                chat_id = callback.message.chat.id

                # Сохраняем принятие в dialog_data
                dialog_manager.dialog_data["user_agreement_accepted"] = True

                self.logger.info(
                    "Пользователь принял пользовательское соглашение",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: chat_id,
                    }
                )

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
                "AuthDialogHandler.accept_privacy_policy",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                chat_id = callback.message.chat.id

                # Сохраняем принятие
                dialog_manager.dialog_data["privacy_policy_accepted"] = True

                self.logger.info(
                    "Пользователь принял политику конфиденциальности",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: chat_id,
                    }
                )

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
                user = callback.from_user

                # Сохраняем принятие
                dialog_manager.dialog_data["data_processing_accepted"] = True

                # Регистрируем пользователя
                authorized_data = await self.kontur_account_client.register(
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

                self.logger.info(
                    "Пользователь завершил процесс авторизации",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: chat_id,
                        common.TELEGRAM_USER_USERNAME_KEY: user.username,
                    }
                )

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
                "AuthDialogHandler.handle_access_denied",
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

    async def get_agreement_data(self, **kwargs) -> dict:
        with self.tracer.start_as_current_span(
                "AuthDialogGetter.get_agreement_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем ссылки на документы из конфига
                data = {
                    "user_agreement_link": f"https://{self.domain}/agreement",
                    "privacy_policy_link": f"https://{self.domain}/privacy",
                    "data_processing_link": f"https://{self.domain}/data-processing",
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_user_status(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "AuthDialogGetter.get_user_status",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                user = dialog_manager.event.from_user
                if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
                    chat_id = dialog_manager.event.message.chat.id
                elif hasattr(dialog_manager.event, 'chat'):
                    chat_id = dialog_manager.event.chat.id
                else:
                    chat_id = None

                data = {
                    "name": user.first_name or "Пользователь",
                    "username": user.username,
                    "chat_id": chat_id,
                    "is_authorized": bool(user_state and user_state.account_id),
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise
