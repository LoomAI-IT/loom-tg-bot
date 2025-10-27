from aiogram_dialog import DialogManager

from internal import interface


class EmployeeManager:
    PERMISSION_MAP = {
        "toggle_required_moderation": "required_moderation",
        "toggle_autoposting": "autoposting",
        "toggle_add_employee": "add_employee",
        "toggle_edit_permissions": "edit_permissions",
        "toggle_top_up_balance": "top_up_balance",
        "toggle_social_networks": "social_networks",
        "toggle_setting_category": "setting_category",
        "toggle_setting_organization": "setting_organization",
    }

    ROLE_NAMES = {
        "employee": "Сотрудник",
        "moderator": "Модератор",
        "admin": "Администратор",
        "owner": "Владелец",
    }

    def __init__(self, logger, loom_employee_client: interface.ILoomEmployeeClient):
        self.logger = logger
        self.loom_employee_client = loom_employee_client

    def toggle_permission(
            self,
            dialog_manager: DialogManager,
            button_id: str
    ) -> bool:
        permission_key = self.PERMISSION_MAP.get(button_id)
        if not permission_key:
            self.logger.info("Разрешение не найдено в маппинге")
            return False

        permissions = dialog_manager.dialog_data.get("temp_permissions", {})
        permissions[permission_key] = not permissions.get(permission_key, False)
        dialog_manager.dialog_data["temp_permissions"] = permissions

        return True

    async def save_permissions(
            self,
            dialog_manager: DialogManager
    ) -> None:
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

        # Очищаем временные данные после сохранения
        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

    def reset_permissions(self, dialog_manager: DialogManager) -> None:
        original = dialog_manager.dialog_data.get("original_permissions", {})
        dialog_manager.dialog_data["temp_permissions"] = original.copy()

    def get_role_display_name(self, role: str) -> str:
        return self.ROLE_NAMES.get(role, role.capitalize())

    async def validate_role_selection(
            self,
            dialog_manager: DialogManager,
            selected_role: str
    ) -> tuple[bool, str | None]:
        selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=selected_account_id
        )

        if employee.role == selected_role:
            self.logger.info("Выбрана роль, которая уже назначена")
            return False, "Эта роль уже назначена сотруднику"

        return True, None

    async def change_role(
            self,
            dialog_manager: DialogManager
    ) -> tuple[bool, str | None]:
        selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))
        new_role = dialog_manager.dialog_data.get("selected_new_role")

        if not new_role:
            self.logger.info("Роль не выбрана")
            return False, "Роль не выбрана"

        await self.loom_employee_client.update_employee_role(
            account_id=selected_account_id,
            role=new_role
        )

        # Очищаем временные данные
        dialog_manager.dialog_data.pop("selected_new_role", None)

        return True, None

    def navigate_employee(
            self,
            dialog_manager: DialogManager,
            button_id: str
    ) -> bool:
        all_employee_ids = dialog_manager.dialog_data.get("all_employee_ids", [])
        current_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

        if not all_employee_ids or current_account_id not in all_employee_ids:
            self.logger.info("Проверка навигации не пройдена")
            return False

        current_index = all_employee_ids.index(current_account_id)

        if button_id == "prev_employee" and current_index > 0:
            self.logger.info("Переход к предыдущему сотруднику")
            new_account_id = all_employee_ids[current_index - 1]
        elif button_id == "next_employee" and current_index < len(all_employee_ids) - 1:
            self.logger.info("Переход к следующему сотруднику")
            new_account_id = all_employee_ids[current_index + 1]
        else:
            return False

        dialog_manager.dialog_data["selected_account_id"] = new_account_id

        # Очищаем временные данные прав при переходе
        dialog_manager.dialog_data.pop("temp_permissions", None)
        dialog_manager.dialog_data.pop("original_permissions", None)

        return True
