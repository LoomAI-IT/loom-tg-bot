from aiogram_dialog import DialogManager

from internal import interface
from . import utils


class AddEmployeeGetter(interface.IAddEmployeeGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client

    async def get_enter_account_id_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            # Current data
            "account_id": dialog_manager.dialog_data.get("account_id", ""),
            "has_account_id": dialog_manager.dialog_data.get("has_account_id", False),

            # Validation error flags
            "has_void_account_id": dialog_manager.dialog_data.get("has_void_account_id", False),
            "has_invalid_account_id": dialog_manager.dialog_data.get("has_invalid_account_id", False),
        }

    async def get_enter_name_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            # Current data
            "account_id": dialog_manager.dialog_data.get("account_id", ""),
            "name": dialog_manager.dialog_data.get("name", ""),
            "has_name": dialog_manager.dialog_data.get("has_name", False),

            # Validation error flags
            "has_void_name": dialog_manager.dialog_data.get("has_void_name", False),
            "has_invalid_name_length": dialog_manager.dialog_data.get("has_invalid_name_length", False),
        }

    async def get_enter_role_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            # Current data
            "account_id": dialog_manager.dialog_data.get("account_id", ""),
            "name": dialog_manager.dialog_data.get("name", ""),
            "has_selected_role": dialog_manager.dialog_data.get("has_selected_role", False),
            "selected_role_display": dialog_manager.dialog_data.get("selected_role_display", ""),

            # Available roles
            "roles": utils.RoleDisplayHelper.ROLE_OPTIONS,
        }

    async def get_permissions_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        employee_data = utils.EmployeeData.from_dialog_data(dialog_manager.dialog_data)

        # Get permission icons based on current state
        permissions_data = dialog_manager.dialog_data.get("permissions", {})
        permissions = utils.Permissions.from_dict(permissions_data)

        return {
            # Employee info
            "account_id": str(employee_data.account_id or ""),
            "name": employee_data.name or "",
            "role": utils.RoleDisplayHelper.get_display_name(employee_data.role) if employee_data.role else "",

            # Permission icons (✅ = enabled, ❌ = disabled)
            "required_moderation_icon": "✅" if not permissions.required_moderation else "❌",
            "autoposting_icon": "✅" if permissions.autoposting else "❌",
            "add_employee_icon": "✅" if permissions.add_employee else "❌",
            "edit_permissions_icon": "✅" if permissions.edit_permissions else "❌",
            "top_up_balance_icon": "✅" if permissions.top_up_balance else "❌",
            "sign_up_social_networks_icon": "✅" if permissions.sign_up_social_networks else "❌",
        }

    async def get_confirm_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        employee_data = utils.EmployeeData.from_dialog_data(dialog_manager.dialog_data)

        # Get formatted permissions text
        permissions_data = dialog_manager.dialog_data.get("permissions", {})
        permissions = utils.Permissions.from_dict(permissions_data)
        permissions_text = self._format_permissions_text(permissions)

        return {
            # Employee info
            "account_id": str(employee_data.account_id or ""),
            "name": employee_data.name or "",
            "role": utils.RoleDisplayHelper.get_display_name(employee_data.role) if employee_data.role else "",
            "permissions_text": permissions_text,
        }

    def _format_permissions_text(self, permissions: utils.Permissions) -> str:
        """Форматирует текст разрешений для отображения"""
        permissions_text_list = []

        permission_checks = [
            (not permissions.required_moderation, "Публикации без одобрения"),
            (permissions.autoposting, "Авто-постинг"),
            (permissions.add_employee, "Добавление сотрудников"),
            (permissions.edit_permissions, "Изменение разрешений"),
            (permissions.top_up_balance, "Пополнение баланса"),
            (permissions.sign_up_social_networks, "Подключение соцсетей"),
        ]

        for has_permission, permission_name in permission_checks:
            if has_permission:
                permissions_text_list.append(f"✅ {permission_name}")
            else:
                permissions_text_list.append(f"❌ {permission_name}")

        if not permissions_text_list:
            permissions_text_list.append("❌ Нет специальных разрешений")

        return "\n".join(permissions_text_list)