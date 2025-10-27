from aiogram_dialog import DialogManager

from internal import interface


class _RoleManager:
    ROLE_NAMES = {
        "employee": "Сотрудник",
        "moderator": "Модератор",
        "admin": "Администратор",
        "owner": "Владелец",
    }

    def __init__(self, logger, loom_employee_client: interface.ILoomEmployeeClient):
        self.logger = logger
        self.loom_employee_client = loom_employee_client

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
