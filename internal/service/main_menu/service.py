from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class MainMenuDialogService(interface.IMainMenuDialogService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_organization_client: interface.IKonturOrganizationClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client

    async def get_main_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Получить данные для главного меню"""
        with self.tracer.start_as_current_span(
                "MainMenuDialogService.get_main_menu_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
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

    async def handle_go_to_content(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Перейти к меню контента"""
        with self.tracer.start_as_current_span(
                "MainMenuDialogService.handle_go_to_content",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Запустить диалог контента
                await callback.answer("Функция контента в разработке", show_alert=True)

                self.logger.info(
                    "Попытка перехода к контенту",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_organization(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuDialogService.handle_go_to_organization",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.OrganizationMenuStates.organization_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info(
                    "Переход к меню организации",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Ошибка при переходе к организации", show_alert=True)
                raise err

    async def handle_go_to_personal_profile(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuDialogService.handle_go_to_personal_profile",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.PersonalProfileStates.personal_profile,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info(
                    "Попытка перехода к личному профилю",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise