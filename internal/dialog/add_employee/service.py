from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode


from internal import interface, model, common
from pkg.trace_wrapper import traced_method
from pkg.log_wrapper import auto_log
from . import utils


class AddEmployeeService(interface.IAddEmployeeService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client

    @auto_log()
    @traced_method()
    async def handle_account_id_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            account_id: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        error_flags = [
            "has_void_account_id",
            "has_invalid_account_id",
            "has_account_id_processing_error"
        ]
        for flag in error_flags:
            dialog_manager.dialog_data.pop(flag, None)

        account_id = account_id.strip()
        if not account_id:
            self.logger.info("Account_id пустой")
            dialog_manager.dialog_data["has_void_account_id"] = True
            return

        try:
            account_id_int = int(account_id)
            if account_id_int <= 0:
                self.logger.info("Account_id меньше или равен 0")
                dialog_manager.dialog_data["has_invalid_account_id"] = True
                return

        except ValueError:
            self.logger.info("Account_id не является числом")
            dialog_manager.dialog_data["has_invalid_account_id"] = True
            return

        dialog_manager.dialog_data["account_id"] = str(account_id_int)
        dialog_manager.dialog_data["has_account_id"] = True

    @auto_log()
    @traced_method()
    async def handle_name_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            name: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        error_flags = [
            "has_void_name",
            "has_invalid_name_length",
            "has_name_processing_error"
        ]
        for flag in error_flags:
            dialog_manager.dialog_data.pop(flag, None)

        name = name.strip()
        if not name:
            self.logger.info("Имя пустое")
            dialog_manager.dialog_data["has_void_name"] = True
            return

        if len(name) < 2 or len(name) > 100:
            self.logger.info("Имя не соответствует требованиям по длине")
            dialog_manager.dialog_data["has_invalid_name_length"] = True
            return

        dialog_manager.dialog_data["name"] = name
        dialog_manager.dialog_data["has_name"] = True

    @auto_log()
    @traced_method()
    async def handle_role_selection(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            role: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        selected_role = common.Role(role)
        dialog_manager.dialog_data["role"] = selected_role.value
        dialog_manager.dialog_data["has_selected_role"] = True
        dialog_manager.dialog_data["selected_role_display"] = utils.RoleDisplayHelper.get_display_name(
            selected_role)

        # Устанавливаем разрешения по умолчанию
        default_permissions = utils.PermissionManager.get_default_permissions(selected_role)
        dialog_manager.dialog_data["permissions"] = default_permissions.to_dict()

    @auto_log()
    @traced_method()
    async def handle_toggle_permission(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        button_id = button.widget_id
        permission_key = utils.PermissionManager.get_permission_key(button_id)

        if not permission_key:
            self.logger.info("Неизвестное разрешение")
            await callback.answer()
            return

        # Получаем и обновляем разрешения
        permissions_data = dialog_manager.dialog_data.get("permissions", {})
        permissions = utils.Permissions.from_dict(permissions_data)

        # Переключаем разрешение
        current_value = getattr(permissions, permission_key)
        setattr(permissions, permission_key, not current_value)

        dialog_manager.dialog_data["permissions"] = permissions.to_dict()

        await callback.answer()

    @auto_log()
    @traced_method()
    async def handle_create_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        # Очищаем предыдущие ошибки
        dialog_manager.dialog_data.pop("has_creation_error", None)
        dialog_manager.dialog_data["is_creating_employee"] = True

        employee_data = utils.EmployeeData.from_dialog_data(dialog_manager.dialog_data)

        # Получаем информацию о текущем пользователе
        chat_id = callback.message.chat.id
        current_user_state = (await self.state_repo.state_by_id(chat_id))[0]
        current_employee = await self.loom_employee_client.get_employee_by_account_id(
            current_user_state.account_id
        )

        # Создаем сотрудника
        await self.loom_employee_client.create_employee(
            organization_id=current_employee.organization_id,
            invited_from_account_id=current_user_state.account_id,
            account_id=employee_data.account_id,
            name=employee_data.name,
            role=employee_data.role.value
        )

        await self.loom_employee_client.update_employee_permissions(
            account_id=employee_data.account_id,
            required_moderation=employee_data.permissions.required_moderation,
            autoposting_permission=employee_data.permissions.autoposting,
            add_employee_permission=employee_data.permissions.add_employee,
            edit_employee_perm_permission=employee_data.permissions.edit_permissions,
            top_up_balance_permission=employee_data.permissions.top_up_balance,
            sign_up_social_net_permission=employee_data.permissions.sign_up_social_networks,
        )

        dialog_manager.dialog_data["is_creating_employee"] = False

        await callback.answer(f"Сотрудник '{employee_data.name}' добавлен в организацию", show_alert=True)

        if await self._check_alerts(dialog_manager):
            self.logger.info("Переход к алертам")
            return

        await dialog_manager.start(
            model.OrganizationMenuStates.organization_menu,
            mode=StartMode.RESET_STACK
        )

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
            self.logger.info("Переход к алертам")
            return

        await dialog_manager.start(
            model.OrganizationMenuStates.organization_menu,
            mode=StartMode.RESET_STACK
        )

    async def _check_alerts(self, dialog_manager: DialogManager) -> bool:
        state = await self._get_state(dialog_manager)
        await self.state_repo.change_user_state(
            state_id=state.id,
            can_show_alerts=True
        )

        vizard_alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(
            state_id=state.id
        )
        if vizard_alerts:
            await dialog_manager.start(
                model.AlertsStates.video_generated_alert,
                mode=StartMode.RESET_STACK
            )
            return True

        return False

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
