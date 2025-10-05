from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class OrganizationMenuService(interface.IOrganizationMenuService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client

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
                state = await self._get_state(dialog_manager)

                employee = await self.loom_employee_client.get_employee_by_account_id(
                    state.account_id,
                )

                if not employee.edit_employee_perm_permission:
                    await callback.answer("У вас нет прав менять права сотрудникам", show_alert=True)
                    return

                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                # Запускаем диалог изменения сотрудников
                await dialog_manager.start(
                    model.ChangeEmployeeStates.employee_list,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Переход к настройкам пользователей")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                
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
                state = await self._get_state(dialog_manager)

                employee = await self.loom_employee_client.get_employee_by_account_id(
                    state.account_id,
                )

                if not employee.add_employee_permission:
                    await callback.answer("У вас нет прав для добавления сотрудников", show_alert=True)
                    return

                await self.state_repo.change_user_state(
                    state_id=state.id,
                    can_show_alerts=False
                )

                await dialog_manager.start(
                    model.AddEmployeeStates.enter_account_id,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Попытка перехода к добавлению сотрудника")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Ошибка", show_alert=True)
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
                dialog_manager.show_mode = ShowMode.EDIT

                await dialog_manager.start(model.AddSocialNetworkStates.select_network)

                self.logger.info("Попытка перехода к социальным сетям")

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
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]
