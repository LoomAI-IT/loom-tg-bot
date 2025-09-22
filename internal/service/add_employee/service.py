from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common
from . import utils


class AddEmployeeDialogService(interface.IAddEmployeeDialogService):
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

    async def handle_account_id_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            account_id: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_account_id_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await message.delete()
                account_id = utils.Validator.validate_account_id(account_id)

                dialog_manager.dialog_data["account_id"] = str(account_id)

                await dialog_manager.switch_to(model.AddEmployeeStates.enter_name, ShowMode.EDIT)
                span.set_status(Status(StatusCode.OK))

            except common.ValidationError as e:
                await message.answer(f"❌ {str(e)} Попробуйте снова.")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                await self._handle_unexpected_error(err, span, message)

    async def handle_name_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            name: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_name_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await message.delete()
                validated_name = utils.Validator.validate_name(name)

                dialog_manager.dialog_data["name"] = validated_name

                await dialog_manager.switch_to(model.AddEmployeeStates.enter_role, ShowMode.EDIT)
                span.set_status(Status(StatusCode.OK))

            except common.ValidationError as e:
                await message.answer(f"❌ {str(e)} Попробуйте снова.")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                await self._handle_unexpected_error(err, span, message)

    async def handle_role_selection(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            role: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_role_selection",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                selected_role = common.Role(role)
                dialog_manager.dialog_data["role"] = selected_role.value

                # Устанавливаем разрешения по умолчанию
                default_permissions = utils.PermissionManager.get_default_permissions(selected_role)
                dialog_manager.dialog_data["permissions"] = default_permissions.to_dict()

                await dialog_manager.switch_to(model.AddEmployeeStates.set_permissions)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                await self._handle_unexpected_error(err, span, callback=callback)

    async def handle_toggle_permission(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_toggle_permission",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                button_id = button.widget_id
                permission_key = utils.PermissionManager.get_permission_key(button_id)

                if not permission_key:
                    await callback.answer("❌ Неизвестное разрешение", show_alert=True)
                    return

                # Получаем и обновляем разрешения
                permissions_data = dialog_manager.dialog_data.get("permissions", {})
                permissions = utils.Permissions.from_dict(permissions_data)

                # Переключаем разрешение
                current_value = getattr(permissions, permission_key)
                setattr(permissions, permission_key, not current_value)

                dialog_manager.dialog_data["permissions"] = permissions.to_dict()

                await dialog_manager.update(dialog_manager.dialog_data)
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                await self._handle_unexpected_error(err, span, callback=callback)

    async def handle_create_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_create_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                employee_data = utils.EmployeeData.from_dialog_data(dialog_manager.dialog_data)

                # Получаем информацию о текущем пользователе
                chat_id = callback.message.chat.id
                current_user_state = (await self.state_repo.state_by_id(chat_id))[0]
                current_employee = await self.kontur_employee_client.get_employee_by_account_id(
                    current_user_state.account_id
                )

                # Создаем сотрудника
                await self.kontur_employee_client.create_employee(
                    organization_id=current_employee.organization_id,
                    invited_from_account_id=current_user_state.account_id,
                    account_id=employee_data.account_id,
                    name=employee_data.name,
                    role=employee_data.role.value
                )

                await self.kontur_employee_client.update_employee_permissions(
                    account_id=employee_data.account_id,
                    required_moderation=not employee_data.permissions.required_moderation,
                    autoposting_permission=employee_data.permissions.autoposting,
                    add_employee_permission=employee_data.permissions.add_employee,
                    edit_employee_perm_permission=employee_data.permissions.edit_permissions,
                    top_up_balance_permission=employee_data.permissions.top_up_balance,
                    sign_up_social_net_permission=employee_data.permissions.sign_up_social_networks,
                )

                await callback.answer(
                    f"✅ Сотрудник {employee_data.name} успешно добавлен!",
                    show_alert=True
                )

                await dialog_manager.start(
                    model.OrganizationMenuStates.organization_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                await self._handle_unexpected_error(
                    err,
                    span,
                    callback=callback,
                    error_message="Ошибка при создании сотрудника"
                )

    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_go_to_organization_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.OrganizationMenuStates.organization_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                await self._handle_unexpected_error(err, span)

    # Data getters
    async def get_enter_account_id_data(self, **kwargs) -> dict:
        return {}

    async def get_enter_name_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "account_id": dialog_manager.dialog_data.get("account_id", ""),
        }

    async def get_enter_role_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        return {
            "account_id": dialog_manager.dialog_data.get("account_id", ""),
            "name": dialog_manager.dialog_data.get("name", ""),
            "roles": utils.RoleDisplayHelper.ROLE_OPTIONS,
        }

    async def get_permissions_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        employee_data = utils.EmployeeData.from_dialog_data(dialog_manager.dialog_data)

        return {
            "account_id": str(employee_data.account_id or ""),
            "name": employee_data.name or "",
            "role": utils.RoleDisplayHelper.get_display_name(employee_data.role) if employee_data.role else "",
            "required_moderation_icon": "✅" if not employee_data.permissions.required_moderation else "❌",
            "autoposting_icon": "✅" if employee_data.permissions.autoposting else "❌",
            "add_employee_icon": "✅" if employee_data.permissions.add_employee else "❌",
            "edit_permissions_icon": "✅" if employee_data.permissions.edit_permissions else "❌",
            "top_up_balance_icon": "✅" if employee_data.permissions.top_up_balance else "❌",
            "sign_up_social_networks_icon": "✅" if employee_data.permissions.sign_up_social_networks else "❌",
        }

    async def get_confirm_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        employee_data = utils.EmployeeData.from_dialog_data(dialog_manager.dialog_data)
        permissions_text = self._format_permissions_text(employee_data.permissions)

        return {
            "account_id": str(employee_data.account_id or ""),
            "name": employee_data.name or "",
            "role": utils.RoleDisplayHelper.get_display_name(employee_data.role) if employee_data.role else "",
            "permissions_text": permissions_text,
        }

    async def _handle_unexpected_error(
            self,
            error: Exception,
            span,
            message: Message = None,
            callback: CallbackQuery = None,
            error_message: str = "Произошла ошибка. Попробуйте снова."
    ) -> None:
        span.record_exception(error)
        span.set_status(Status(StatusCode.ERROR, str(error)))

        if message:
            await message.answer(f"❌ {error_message}")
        elif callback:
            await callback.answer(f"❌ {error_message}", show_alert=True)

        raise error

    def _format_permissions_text(self, permissions: utils.Permissions) -> str:
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
