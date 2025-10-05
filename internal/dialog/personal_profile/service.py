from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class PersonalProfileService(interface.IPersonalProfileService):
    def __init__(
            self,
            tel: interface.ITelemetry,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

    async def handle_go_faq(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "PersonalProfileService.handle_go_faq",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки перехода в FAQ")

                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.switch_to(model.PersonalProfileStates.faq)

                await callback.answer("FAQ открыт")

                self.logger.info("Завершение обработки перехода в FAQ")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_support(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "PersonalProfileService.handle_go_to_support",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки перехода в поддержку")

                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.switch_to(model.PersonalProfileStates.support)

                await callback.answer("Техподдержка открыта")

                self.logger.info("Завершение обработки перехода в поддержку")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_back_to_profile(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "PersonalProfileService.handle_back_to_profile",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки возврата в личный профиль")

                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.switch_to(model.PersonalProfileStates.personal_profile)

                await callback.answer("Возврат в профиль")

                self.logger.info("Завершение обработки возврата в личный профиль")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "PersonalProfileService.handle_go_to_main_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки перехода в главное меню")

                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.start(
                    model.MainMenuStates.main_menu,
                    mode=StartMode.RESET_STACK
                )

                await callback.answer("Главное меню открыто")

                self.logger.info("Завершение обработки перехода в главное меню")
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise