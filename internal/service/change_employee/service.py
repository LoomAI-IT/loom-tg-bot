# internal/service/change_employee/service.py
from typing import Any
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class ChangeEmployeeDialogService(interface.IChangeEmployeeDialogService):
    """Сервис для работы с диалогом изменения сотрудников"""

    def __init__(
            self,
            tel: interface.ITelemetry,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_organization_client: interface.IKonturOrganizationClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client

    async def get_employee_list_data(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
            **kwargs
    ) -> dict:
        """Получить данные для окна списка сотрудников"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.get_employee_list_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем организацию пользователя
                organization = await self.kontur_organization_client.get_organization_by_account_id(
                    user_state.account_id
                )

                # Получаем список сотрудников
                employees = await self.kontur_employee_client.get_employees_by_organization(
                    organization.id
                )

                # Фильтруем по поисковому запросу, если есть
                search_query = dialog_manager.dialog_data.get("search_query", "")
                if search_query:
                    employees = [e for e in employees if search_query.lower() in e.name.lower()]

                # Форматируем данные для отображения
                employees_data = [
                    {
                        "id": str(emp.id),
                        "name": emp.name,
                        "role": emp.role,
                    }
                    for emp in employees
                ]

                data = {
                    "employees": employees_data,
                    "employees_count": len(employees_data),
                    "organization_name": organization.name,
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_employee_detail_data(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
            **kwargs
    ) -> dict:
        """Получить детальные данные сотрудника"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.get_employee_detail_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                employee_id = int(dialog_manager.dialog_data.get("selected_employee_id"))

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_id(employee_id)

                # Формируем текст разрешений
                permissions_list = []
                if not employee.required_moderation:
                    permissions_list.append("✅ Публикации без одобрения")
                if employee.autoposting_permission:
                    permissions_list.append("✅ Включить авто-постинг")
                if employee.add_employee_permission:
                    permissions_list.append("✅ Добавлять сотрудников")
                if employee.edit_employee_perm_permission:
                    permissions_list.append("✅ Изменять разрешения сотрудников")
                if employee.top_up_balance_permission:
                    permissions_list.append("✅ Пополнять баланс")
                if employee.sign_up_social_net_permission:
                    permissions_list.append("✅ Подключать социальные сети")

                permissions_text = "\n".join(permissions_list) if permissions_list else "❌ Нет разрешений"

                data = {
                    "username": employee.name,
                    "publications_count": 0,  # TODO: Получить из API публикаций
                    "generations_count": 0,  # TODO: Получить из API публикаций
                    "permissions_text": permissions_text,
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_permissions_data(
            self,
            dialog_manager: DialogManager,
            user_state: model.UserState,
            **kwargs
    ) -> dict:
        """Получить данные для окна изменения разрешений"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.get_permissions_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                employee_id = int(dialog_manager.dialog_data.get("selected_employee_id"))

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_id(employee_id)

                # Получаем текущие значения разрешений из dialog_data или из сотрудника
                permissions = dialog_manager.dialog_data.get("permissions", {
                    "no_moderation": not employee.required_moderation,
                    "autoposting": employee.autoposting_permission,
                    "add_employee": employee.add_employee_permission,
                    "edit_permissions": employee.edit_employee_perm_permission,
                    "top_up_balance": employee.top_up_balance_permission,
                    "social_networks": employee.sign_up_social_net_permission,
                })

                data = {
                    "username": employee.name,
                    "publications_count": 0,  # TODO: Получить из API
                    "generations_count": 0,  # TODO: Получить из API
                    "no_moderation_icon": "✅" if permissions["no_moderation"] else "❌",
                    "autoposting_icon": "✅" if permissions["autoposting"] else "❌",
                    "add_employee_icon": "✅" if permissions["add_employee"] else "❌",
                    "edit_permissions_icon": "✅" if permissions["edit_permissions"] else "❌",
                    "top_up_balance_icon": "✅" if permissions["top_up_balance"] else "❌",
                    "social_networks_icon": "✅" if permissions["social_networks"] else "❌",
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_select_employee(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            employee_id: str
    ) -> None:
        """Обработать выбор сотрудника из списка"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_select_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Сохраняем ID выбранного сотрудника
                dialog_manager.dialog_data["selected_employee_id"] = employee_id

                # Переходим к деталям сотрудника
                await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_detail)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Произошла ошибка при выборе сотрудника", show_alert=True)
                raise

    async def handle_search_employee(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            search_query: str
    ) -> None:
        """Обработать поиск сотрудника"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_search_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Сохраняем поисковый запрос
                dialog_manager.dialog_data["search_query"] = search_query

                # Обновляем окно
                await dialog_manager.update()

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_toggle_permission(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Переключить разрешение"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_toggle_permission",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                button_id = button.widget_id

                # Получаем текущие разрешения
                employee_id = int(dialog_manager.dialog_data.get("selected_employee_id"))
                employee = await self.kontur_employee_client.get_employee_by_id(employee_id)

                permissions = dialog_manager.dialog_data.get("permissions", {
                    "no_moderation": not employee.required_moderation,
                    "autoposting": employee.autoposting_permission,
                    "add_employee": employee.add_employee_permission,
                    "edit_permissions": employee.edit_employee_perm_permission,
                    "top_up_balance": employee.top_up_balance_permission,
                    "social_networks": employee.sign_up_social_net_permission,
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
                await dialog_manager.update()

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Произошла ошибка", show_alert=True)
                raise

    async def handle_save_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Сохранить изменения разрешений"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_save_permissions",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                employee_id = int(dialog_manager.dialog_data.get("selected_employee_id"))
                permissions = dialog_manager.dialog_data.get("permissions", {})

                # Обновляем разрешения через API
                await self.kontur_employee_client.update_employee_permissions(
                    employee_id=employee_id,
                    required_moderation=not permissions.get("no_moderation", False),
                    autoposting_permission=permissions.get("autoposting", False),
                    add_employee_permission=permissions.get("add_employee", False),
                    edit_employee_perm_permission=permissions.get("edit_permissions", False),
                    top_up_balance_permission=permissions.get("top_up_balance", False),
                    sign_up_social_net_permission=permissions.get("social_networks", False),
                )

                await callback.answer("✅ Разрешения успешно обновлены!", show_alert=True)

                # Возвращаемся к деталям сотрудника
                await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_detail)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при сохранении разрешений", show_alert=True)
                raise

    async def handle_delete_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Удалить сотрудника"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_delete_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                employee_id = int(dialog_manager.dialog_data.get("selected_employee_id"))

                # Удаляем сотрудника
                await self.kontur_employee_client.delete_employee(employee_id)

                await callback.answer("✅ Сотрудник успешно удален!", show_alert=True)

                # Возвращаемся к списку
                await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_list)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при удалении сотрудника", show_alert=True)
                raise

    async def handle_pagination(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработать навигацию между сотрудниками"""
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_pagination",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                button_id = button.widget_id

                if button_id == "refresh_list":
                    # Очищаем поисковый запрос и обновляем список
                    dialog_manager.dialog_data.pop("search_query", None)
                    await dialog_manager.update()
                elif button_id in ["prev_employee", "next_employee"]:
                    # TODO: Реализовать переход к предыдущему/следующему сотруднику
                    await callback.answer("В разработке", show_alert=False)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise