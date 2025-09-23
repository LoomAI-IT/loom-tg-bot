from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class OrganizationMenuService(interface.IOrganizationMenuService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo

    async def handle_go_to_employee_settings(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationMenuService.handle_go_to_employee_settings",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Запускаем диалог изменения сотрудников
                await dialog_manager.start(
                    model.ChangeEmployeeStates.employee_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Переход к настройкам пользователей")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Ошибка при переходе к настройкам", show_alert=True)
                raise

    async def handle_go_to_add_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationMenuService.handle_go_to_add_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.AddEmployeeStates.enter_account_id,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Попытка перехода к добавлению сотрудника")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_top_up_balance(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationMenuService.handle_go_to_top_up_balance",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Запустить диалог пополнения баланса
                await callback.answer("Функция в разработке", show_alert=True)

                self.logger.info("Попытка перехода к пополнению баланса")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_social_networks(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationMenuService.handle_go_to_social_networks",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Запустить диалог управления социальными сетями
                await callback.answer("Функция в разработке", show_alert=True)

                self.logger.info("Попытка перехода к социальным сетям")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationMenuService.handle_go_to_main_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.MainMenuStates.main_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Переход в главное меню")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

