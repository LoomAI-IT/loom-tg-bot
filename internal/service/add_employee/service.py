# internal/service/add_employee/service.py
import re
from typing import Any
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class AddEmployeeDialogService(interface.IAddEmployeeDialogService):

    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_account_client: interface.IKonturAccountClient,
            kontur_employee_client: interface.IKonturEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_account_client = kontur_account_client
        self.kontur_employee_client = kontur_employee_client

    async def handle_account_id_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            account_id: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_username_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:

                if not account_id:
                    await message.answer("❌ Username не может быть пустым. Попробуйте снова.")
                    return

                # Сохраняем username в данные диалога
                dialog_manager.dialog_data["account_id"] = account_id

                self.logger.info(
                    "Username сотрудника введен",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "account_id": account_id,
                    }
                )

                # Переходим к следующему шагу
                await dialog_manager.switch_to(model.AddEmployeeStates.enter_name)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Произошла ошибка. Попробуйте снова.")
                raise

    async def handle_name_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            name: str
    ) -> None:
        """Обработать ввод имени"""
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_name_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                name = name.strip()

                # Валидация имени
                if not name:
                    await message.answer("❌ Имя не может быть пустым. Попробуйте снова.")
                    return

                if len(name) < 2 or len(name) > 100:
                    await message.answer("❌ Имя должно быть от 2 до 100 символов.")
                    return

                # Сохраняем имя в данные диалога
                dialog_manager.dialog_data["name"] = name

                self.logger.info(
                    "Имя сотрудника введено",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "name": name,
                    }
                )

                # Переходим к выбору роли
                await dialog_manager.switch_to(model.AddEmployeeStates.enter_role)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await message.answer("❌ Произошла ошибка. Попробуйте снова.")
                raise

    async def handle_role_selection(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            role: str
    ) -> None:
        """Обработать выбор роли"""
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_role_selection",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Сохраняем роль
                dialog_manager.dialog_data["role"] = role

                # Инициализируем разрешения по умолчанию в зависимости от роли
                default_permissions = self._get_default_permissions_by_role(role)
                dialog_manager.dialog_data["permissions"] = default_permissions

                self.logger.info(
                    "Роль сотрудника выбрана",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "role": role,
                    }
                )

                # Переходим к настройке разрешений
                await dialog_manager.switch_to(model.AddEmployeeStates.set_permissions)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Произошла ошибка", show_alert=True)
                raise

    async def handle_toggle_permission(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Переключить разрешение"""
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_toggle_permission",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                button_id = button.widget_id

                # Получаем текущие разрешения
                permissions = dialog_manager.dialog_data.get("permissions", {
                    "no_moderation": False,
                    "autoposting": False,
                    "add_employee": False,
                    "edit_permissions": False,
                    "top_up_balance": False,
                    "social_networks": False,
                })

                # Определяем какое разрешение переключаем
                permission_map = {
                    "toggle_no_moderation": "no_moderation",
                    "no_moderation_label": "no_moderation",
                    "toggle_autoposting": "autoposting",
                    "autoposting_label": "autoposting",
                    "toggle_add_employee": "add_employee",
                    "add_employee_label": "add_employee",
                    "toggle_edit_permissions": "edit_permissions",
                    "edit_permissions_label": "edit_permissions",
                    "toggle_top_up_balance": "top_up_balance",
                    "top_up_balance_label": "top_up_balance",
                    "toggle_social_networks": "social_networks",
                    "social_networks_label": "social_networks",
                }

                permission_key = permission_map.get(button_id)
                if permission_key:
                    permissions[permission_key] = not permissions[permission_key]
                    dialog_manager.dialog_data["permissions"] = permissions

                # Обновляем окно
                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Произошла ошибка", show_alert=True)
                raise

    async def handle_create_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Создать сотрудника"""
        with self.tracer.start_as_current_span(
                "AddEmployeeDialogService.handle_create_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем данные из диалога
                username = dialog_manager.dialog_data.get("username")
                name = dialog_manager.dialog_data.get("name")
                role = dialog_manager.dialog_data.get("role")
                permissions = dialog_manager.dialog_data.get("permissions", {})

                # Получаем информацию о текущем пользователе
                if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
                    chat_id = dialog_manager.event.message.chat.id
                elif hasattr(dialog_manager.event, 'chat'):
                    chat_id = dialog_manager.event.chat.id
                else:
                    chat_id = None

                current_user_state = (await self.state_repo.state_by_id(chat_id))[0]

                # Получаем текущего сотрудника (который добавляет)
                current_employee = await self.kontur_employee_client.get_employee_by_account_id(
                    current_user_state.account_id
                )

                # TODO: Здесь нужно получить account_id по username
                # Это требует дополнительного API в kontur_account_client
                # Пока используем заглушку
                new_employee_account_id = 12345  # Заглушка

                # Создаем сотрудника
                employee_id = await self.kontur_employee_client.create_employee(
                    organization_id=current_employee.organization_id,
                    invited_from_account_id=current_user_state.account_id,
                    account_id=new_employee_account_id,
                    name=name,
                    role=role
                )

                # Устанавливаем разрешения
                await self.kontur_employee_client.update_employee_permissions(
                    employee_id=employee_id,
                    required_moderation=not permissions.get("no_moderation", False),
                    autoposting_permission=permissions.get("autoposting", False),
                    add_employee_permission=permissions.get("add_employee", False),
                    edit_employee_perm_permission=permissions.get("edit_permissions", False),
                    top_up_balance_permission=permissions.get("top_up_balance", False),
                    sign_up_social_net_permission=permissions.get("social_networks", False),
                )

                self.logger.info(
                    "Новый сотрудник создан",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: chat_id,
                        "employee_id": employee_id,
                        "username": username,
                        "name": name,
                        "role": role,
                    }
                )

                await callback.answer(
                    f"✅ Сотрудник {name} успешно добавлен!",
                    show_alert=True
                )

                # Возвращаемся в меню организации
                await dialog_manager.start(
                    model.OrganizationMenuStates.organization_menu,
                    mode=StartMode.RESET_STACK
                )

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при создании сотрудника", show_alert=True)
                raise

    def _get_default_permissions_by_role(self, role: str) -> dict:
        """Получить разрешения по умолчанию для роли"""
        if role == "admin":
            return {
                "no_moderation": True,
                "autoposting": True,
                "add_employee": True,
                "edit_permissions": True,
                "top_up_balance": True,
                "social_networks": True,
            }
        elif role == "moderator":
            return {
                "no_moderation": True,
                "autoposting": True,
                "add_employee": False,
                "edit_permissions": False,
                "top_up_balance": False,
                "social_networks": True,
            }
        elif role == "employee":
            return {
                "no_moderation": False,
                "autoposting": False,
                "add_employee": False,
                "edit_permissions": False,
                "top_up_balance": False,
                "social_networks": False,
            }
        else:  # default
            return {
                "no_moderation": False,
                "autoposting": False,
                "add_employee": False,
                "edit_permissions": False,
                "top_up_balance": False,
                "social_networks": False,
            }

    async def get_enter_account_id_data(self, **kwargs) -> dict:
        """Данные для окна ввода username"""
        return {}

    async def get_enter_name_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для окна ввода имени"""
        return {
            "username": dialog_manager.dialog_data.get("username", ""),
        }

    async def get_enter_role_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для окна выбора роли"""
        roles = [
            {"value": "employee", "title": "👤 Сотрудник"},
            {"value": "moderator", "title": "👨‍💼 Модератор"},
            {"value": "admin", "title": "👑 Администратор"},
        ]

        return {
            "username": dialog_manager.dialog_data.get("username", ""),
            "name": dialog_manager.dialog_data.get("name", ""),
            "roles": roles,
        }

    async def get_permissions_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        """Данные для окна настройки разрешений"""
        permissions = dialog_manager.dialog_data.get("permissions", {
            "no_moderation": False,
            "autoposting": False,
            "add_employee": False,
            "edit_permissions": False,
            "top_up_balance": False,
            "social_networks": False,
        })

        # Получаем читаемое название роли
        role_names = {
            "employee": "Сотрудник",
            "manager": "Менеджер",
            "admin": "Администратор",
        }
        role = dialog_manager.dialog_data.get("role", "employee")
        role_display = role_names.get(role, role)

        return {
            "username": dialog_manager.dialog_data.get("username", ""),
            "name": dialog_manager.dialog_data.get("name", ""),
            "role": role_display,
            "no_moderation_icon": "✅" if permissions["no_moderation"] else "❌",
            "autoposting_icon": "✅" if permissions["autoposting"] else "❌",
            "add_employee_icon": "✅" if permissions["add_employee"] else "❌",
            "edit_permissions_icon": "✅" if permissions["edit_permissions"] else "❌",
            "top_up_balance_icon": "✅" if permissions["top_up_balance"] else "❌",
            "social_networks_icon": "✅" if permissions["social_networks"] else "❌",
        }