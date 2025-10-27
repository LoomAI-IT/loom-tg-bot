from aiogram_dialog import DialogManager

from internal import interface


class _PermissionManager:
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
