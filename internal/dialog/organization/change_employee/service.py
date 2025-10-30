from typing import Any

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager, AlertsManager

from internal.dialog.organization.change_employee.helpers import EmployeeManager



class ChangeEmployeeService(interface.IChangeEmployeeService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client

        # Инициализация приватных сервисов
        self.state_manager = StateManager(
            self.state_repo
        )
        self.alerts_manager = AlertsManager(
            self.state_repo
        )
        self.employee_manager = EmployeeManager(
            self.logger,
            self.loom_employee_client
        )

    @auto_log()
    @traced_method()
    async def handle_select_employee(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            employee_id: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        dialog_manager.dialog_data["selected_account_id"] = employee_id

        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

        await dialog_manager.switch_to(state=model.ChangeEmployeeStates.employee_detail)

    @auto_log()
    @traced_method()
    async def handle_search_employee(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            search_query: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        dialog_manager.dialog_data["search_query"] = search_query.strip()

    @auto_log()
    @traced_method()
    async def handle_clear_search(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        dialog_manager.dialog_data.pop("search_query", None)
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_refresh_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.logger.info("Начало обновления списка сотрудников")

        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await callback.answer()
        self.logger.info("Завершение обновления списка сотрудников")

    @auto_log()
    @traced_method()
    async def handle_navigate_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.employee_manager.navigate_employee(
            dialog_manager=dialog_manager, 
            button_id=button.widget_id
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        state = await self.state_manager.get_state(dialog_manager=dialog_manager)
        if await self.alerts_manager.check_alerts(dialog_manager=dialog_manager, state=state):
            self.logger.info("Обнаружены алерты, переход прерван")
            return

        await dialog_manager.start(
            state=model.OrganizationMenuStates.organization_menu,
            mode=StartMode.RESET_STACK
        )


    @auto_log()
    @traced_method()
    async def handle_toggle_permission(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.employee_manager.toggle_permission(
            dialog_manager=dialog_manager, 
            button_id=button.widget_id
        )
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_save_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await self.employee_manager.save_permissions(dialog_manager=dialog_manager)
        # TODO сделать вебхук для алерта об изменении прав

        await callback.answer("Разрешения успешно сохранены", show_alert=True)
        await dialog_manager.switch_to(state=model.ChangeEmployeeStates.employee_detail)

    @auto_log()
    @traced_method()
    async def handle_reset_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        self.employee_manager.reset_permissions(dialog_manager=dialog_manager)
        await callback.answer("Изменения отменены", show_alert=True)

    @auto_log()
    @traced_method()
    async def handle_show_role_change(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        dialog_manager.dialog_data.pop("selected_new_role", None)
        await dialog_manager.switch_to(state=model.ChangeEmployeeStates.change_role)

    @auto_log()
    @traced_method()
    async def handle_select_role(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            role: str
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        is_valid, error_message = await self.employee_manager.validate_role_selection(
            dialog_manager=dialog_manager,
            selected_role=role
        )

        if not is_valid:
            await callback.answer(error_message, show_alert=True)
            return

        dialog_manager.dialog_data["selected_new_role"] = role
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_reset_role_selection(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
        dialog_manager.dialog_data.pop("selected_new_role", None)
        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_confirm_role_change(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        success, error_message = await self.employee_manager.change_role(dialog_manager=dialog_manager)

        if not success:
            await callback.answer(error_message, show_alert=True)
            return

        # TODO сделать вебхук для алерта об изменении роли

        await callback.answer("Роль успешно изменена", show_alert=True)
        await dialog_manager.switch_to(state=model.ChangeEmployeeStates.employee_detail)

    @auto_log()
    @traced_method()
    async def handle_delete_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

        await self.loom_employee_client.delete_employee(account_id=selected_account_id)

        dialog_manager.dialog_data.pop("selected_account_id", None)
        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

        await callback.answer("Сотрудник успешно удален", show_alert=True)
        await dialog_manager.switch_to(state=model.ChangeEmployeeStates.employee_list)
