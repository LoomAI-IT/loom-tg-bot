import uuid
from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, common, model


class AuthDialogHandler(interface.IAuthDialogHandler):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_service: interface.IStateService,
            account_client: interface.IAccountClient,
            organization_client: interface.IOrganizationClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_service = state_service
        self.account_client = account_client
        self.organization_client = organization_client

    async def accept_user_agreement(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Принять пользовательское соглашение и перейти к политике конфиденциальности"""
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
        """Принять политику конфиденциальности и перейти к согласию на обработку данных"""
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
            dialog_manager: DialogManager
    ) -> None:
        """Принять согласие на обработку данных и завершить авторизацию"""
        with self.tracer.start_as_current_span(
                "AuthDialogHandler.accept_data_processing",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                chat_id = callback.message.chat.id
                user = callback.from_user

                # Сохраняем принятие
                dialog_manager.dialog_data["data_processing_accepted"] = True

                authorized_data = await self.account_client.register(
                    uuid.uuid4().hex,
                    uuid.uuid4().hex,
                )

                await self.state_service.change_user_state(
                    chat_id,
                    authorized_data.account_id,
                    authorized_data.access_token,
                    authorized_data.refresh_token
                )

                self.logger.info(
                    "Пользователь завершил процесс авторизации",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: chat_id,
                        common.TELEGRAM_USER_USERNAME_KEY: user.username,
                    }
                )

                organization = await self.organization_client.get_organization_by_account_id(authorized_data.account_id)

                if organization:
                    # Переходим к приветственному окну
                    await dialog_manager.switch_to(model.AuthStates.welcome)
                else:
                    # Переходим к окну отказа в доступе
                    await dialog_manager.switch_to(model.AuthStates.access_denied)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Произошла ошибка. Попробуйте снова.", show_alert=True)
                raise

    async def handle_access_denied(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработать отказ в доступе"""
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

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise