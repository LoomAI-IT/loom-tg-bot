from aiogram.types import CallbackQuery

from internal import interface, model


class _PermissionChecker:
    def __init__(self, logger, loom_employee_client: interface.ILoomEmployeeClient):
        self.logger = logger
        self.loom_employee_client = loom_employee_client

    async def check_employee_settings_permission(
            self,
            state: model.UserState,
            callback: CallbackQuery
    ) -> bool:
        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=state.account_id,
        )

        if not employee.edit_employee_perm_permission:
            self.logger.info("Отказано в доступе к управлению сотрудниками")
            await callback.answer("Недостаточно прав для управления сотрудниками", show_alert=True)
            return False
        return True

    async def check_update_organization_permission(
            self,
            state: model.UserState,
            callback: CallbackQuery
    ) -> bool:
        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=state.account_id
        )

        if not employee.setting_category_permission:
            self.logger.info("Отказано в доступе к обновлению организации")
            await callback.answer("У вас нет прав обновлять организацию", show_alert=True)
            return False
        return True

    async def check_update_category_permission(
            self,
            state: model.UserState,
            callback: CallbackQuery
    ) -> bool:
        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=state.account_id
        )

        if not employee.setting_category_permission:
            self.logger.info("Отказано в доступе к обновлению рубрик")
            await callback.answer("У вас нет прав обновлять рубрики", show_alert=True)
            return False
        return True

    async def check_add_employee_permission(
            self,
            state: model.UserState,
            callback: CallbackQuery
    ) -> bool:
        employee = await self.loom_employee_client.get_employee_by_account_id(
            account_id=state.account_id,
        )

        if not employee.add_employee_permission:
            self.logger.info("Отказано в доступе к добавлению сотрудников")
            await callback.answer("Недостаточно прав для добавления сотрудников", show_alert=True)
            return False
        return True
