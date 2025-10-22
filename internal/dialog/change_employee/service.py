from typing import Any

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


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

    @auto_log()
    @traced_method()
    async def handle_select_employee(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            employee_id: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        dialog_manager.dialog_data["selected_account_id"] = employee_id

        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

        await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_detail)

    @auto_log()
    @traced_method()
    async def handle_search_employee(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            search_query: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT
        dialog_manager.dialog_data["search_query"] = search_query.strip()

    @auto_log()
    @traced_method()
    async def handle_clear_search(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT
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

        dialog_manager.show_mode = ShowMode.EDIT

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
        dialog_manager.show_mode = ShowMode.EDIT

        button_id = button.widget_id
        all_employee_ids = dialog_manager.dialog_data.get("all_employee_ids", [])
        current_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

        if not all_employee_ids or current_account_id not in all_employee_ids:
            self.logger.info("Проверка навигации не пройдена")
            return

        current_index = all_employee_ids.index(current_account_id)

        if button_id == "prev_employee" and current_index > 0:
            self.logger.info("Переход к предыдущему сотруднику")
            new_account_id = all_employee_ids[current_index - 1]
        elif button_id == "next_employee" and current_index < len(all_employee_ids) - 1:
            self.logger.info("Переход к следующему сотруднику")
            new_account_id = all_employee_ids[current_index + 1]
        else:
            return

        dialog_manager.dialog_data["selected_account_id"] = new_account_id

        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

    @auto_log()
    @traced_method()
    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        if await self._check_alerts(dialog_manager):
            self.logger.info("Обнаружены алерты, переход прерван")
            return

        await dialog_manager.start(
            model.OrganizationMenuStates.organization_menu,
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
        dialog_manager.show_mode = ShowMode.EDIT

        permission_map = {
            "toggle_required_moderation": "required_moderation",
            "toggle_autoposting": "autoposting",
            "toggle_add_employee": "add_employee",
            "toggle_edit_permissions": "edit_permissions",
            "toggle_top_up_balance": "top_up_balance",
            "toggle_social_networks": "social_networks",
            "toggle_setting_category": "setting_category",
            "toggle_setting_organization": "setting_organization",
        }

        permission_key = permission_map.get(button.widget_id)
        if not permission_key:
            self.logger.info("Разрешение не найдено в маппинге")
            return

        permissions = dialog_manager.dialog_data.get("temp_permissions", {})

        permissions[permission_key] = not permissions.get(permission_key, False)
        dialog_manager.dialog_data["temp_permissions"] = permissions

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_save_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))
        permissions = dialog_manager.dialog_data.get("temp_permissions", {})

        await self.loom_employee_client.update_employee_permissions(
            account_id=selected_account_id,
            required_moderation=permissions.get("required_moderation", False),
            autoposting_permission=permissions.get("autoposting", False),
            add_employee_permission=permissions.get("add_employee", False),
            edit_employee_perm_permission=permissions.get("edit_permissions", False),
            top_up_balance_permission=permissions.get("top_up_balance", False),
            sign_up_social_net_permission=permissions.get("social_networks", False),
            setting_category_permission=permissions.get("setting_category", False),
            setting_organization_permission=permissions.get("setting_organization", False),
        )
        # TODO сделать вебхук для алерта об изменении прав

        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

        await callback.answer("Разрешения успешно сохранены", show_alert=True)
        await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_detail)

    @auto_log()
    @traced_method()
    async def handle_reset_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT
        original = dialog_manager.dialog_data.get("original_permissions", {})
        dialog_manager.dialog_data["temp_permissions"] = original.copy()
        await callback.answer("Изменения отменены", show_alert=True)

    @auto_log()
    @traced_method()
    async def handle_show_role_change(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT
        dialog_manager.dialog_data.pop("selected_new_role", None)
        await dialog_manager.switch_to(model.ChangeEmployeeStates.change_role)

    @auto_log()
    @traced_method()
    async def handle_select_role(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            role: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

        employee = await self.loom_employee_client.get_employee_by_account_id(
            selected_account_id
        )

        if employee.role == role:
            self.logger.info("Выбрана роль, которая уже назначена")
            await callback.answer("Эта роль уже назначена сотруднику", show_alert=True)
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
        dialog_manager.show_mode = ShowMode.EDIT
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
        dialog_manager.show_mode = ShowMode.EDIT

        selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))
        new_role = dialog_manager.dialog_data.get("selected_new_role")

        if not new_role:
            self.logger.info("Роль не выбрана")
            await callback.answer("Роль не выбрана", show_alert=True)
            return

        await self.loom_employee_client.update_employee_role(
            account_id=selected_account_id,
            role=new_role
        )
        # TODO сделать вебхук для алерта об изменении роли

        dialog_manager.dialog_data.pop("selected_new_role", None)

        await callback.answer(f"Роль успешно изменена", show_alert=True)
        await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_detail)

    @auto_log()
    @traced_method()
    async def handle_delete_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

        await self.loom_employee_client.delete_employee(selected_account_id)

        employee_state = await self.state_repo.state_by_account_id(selected_account_id)
        if employee_state:
            self.logger.info("Обновление состояния удаленного сотрудника")
            await self.state_repo.change_user_state(
                employee_state[0].id,
                organization_id=0
            )
            # TODO сделать вебух и отправлять удаление туда, это должно далться в вебхуке


        dialog_manager.dialog_data.pop("selected_account_id", None)
        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

        await callback.answer(f"Сотрудник успешно удален",show_alert=True)
        await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_list)

    async def _check_alerts(self, dialog_manager: DialogManager) -> bool:
        state = await self._get_state(dialog_manager)

        publication_approved_alerts = await self.state_repo.get_publication_approved_alert_by_state_id(
            state_id=state.id
        )
        if publication_approved_alerts:
            await dialog_manager.start(
                model.AlertsStates.publication_approved_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        publication_rejected_alerts = await self.state_repo.get_publication_rejected_alert_by_state_id(
            state_id=state.id
        )
        if publication_rejected_alerts:
            await dialog_manager.start(
                model.AlertsStates.publication_rejected_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        vizard_alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(
            state_id=state.id
        )
        if vizard_alerts:
            await dialog_manager.start(
                model.AlertsStates.video_generated_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=True
        )

        return False

    def _get_role_display_name(self, role: str) -> str:
        role_names = {
            "employee": "Сотрудник",
            "moderator": "Модератор",
            "admin": "Администратор",
            "owner": "Владелец",
        }
        return role_names.get(role, role.capitalize())

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
