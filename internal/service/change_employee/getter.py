from datetime import datetime

from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ChangeEmployeeGetter(interface.IChangeEmployeeGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_organization_client: interface.IKonturOrganizationClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client

    async def get_employee_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeGetter.get_employee_list_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                state = await self._get_state(dialog_manager)
                current_employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                organization = await self.kontur_organization_client.get_organization_by_id(
                    current_employee.organization_id
                )

                # Получаем список всех сотрудников организации
                all_employees = await self.kontur_employee_client.get_employees_by_organization(
                    organization.id
                )

                # Фильтрация по поисковому запросу
                search_query = dialog_manager.dialog_data.get("search_query", "")
                if search_query:
                    filtered_employees = [
                        e for e in all_employees
                        if search_query.lower() in e.name.lower()
                    ]
                else:
                    filtered_employees = all_employees

                # Сохраняем полный список для навигации
                dialog_manager.dialog_data["all_employee_ids"] = [
                    e.account_id for e in filtered_employees
                ]

                # Форматируем данные для отображения
                employees_data = []
                for emp in filtered_employees:
                    role_display = self._get_role_display_name(emp.role)
                    employees_data.append({
                        "account_id": emp.account_id,
                        "name": emp.name,
                        "role": emp.role,
                        "role_display": role_display,
                    })

                data = {
                    "employees": employees_data,
                    "employees_count": len(all_employees),
                    "filtered_count": len(filtered_employees),
                    "organization_name": organization.name,
                    "has_search": bool(search_query),
                    "search_query": search_query,
                    "show_pager": len(employees_data) > 6,
                }

                self.logger.info("Список сотрудников загружен")

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_employee_detail_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeGetter.get_employee_detail_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

                # Получаем текущего пользователя
                state = await self._get_state(dialog_manager)
                current_employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # Получаем выбранного сотрудника
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    selected_account_id
                )

                # Получаем статистику (заглушка, замените на реальные вызовы API)
                publications_count = 0  # TODO: await self.kontur_content_client.get_publications_count(selected_account_id)
                generations_count = 0  # TODO: await self.kontur_content_client.get_generations_count(selected_account_id)

                # Формируем список разрешений
                permissions_list = []
                if not employee.required_moderation:
                    permissions_list.append("✅ Публикации без модерации")
                if employee.autoposting_permission:
                    permissions_list.append("✅ Авто-постинг")
                if employee.add_employee_permission:
                    permissions_list.append("✅ Добавление сотрудников")
                if employee.edit_employee_perm_permission:
                    permissions_list.append("✅ Изменение разрешений")
                if employee.top_up_balance_permission:
                    permissions_list.append("✅ Пополнение баланса")
                if employee.sign_up_social_net_permission:
                    permissions_list.append("✅ Подключение соцсетей")

                if not permissions_list:
                    permissions_list.append("❌ Нет специальных разрешений")

                permissions_text = "\n".join(permissions_list)

                # Навигация
                all_employee_ids = dialog_manager.dialog_data.get("all_employee_ids", [])
                current_index = all_employee_ids.index(
                    selected_account_id) + 1 if selected_account_id in all_employee_ids else 1

                # Форматируем дату
                created_at = employee.created_at
                if isinstance(created_at, str):
                    try:
                        created_date = datetime.fromisoformat(created_at)
                        created_at = created_date.strftime("%d.%m.%Y")
                    except:
                        created_at = "неизвестно"

                # Проверяем права на действия
                is_current_user = (state.account_id == selected_account_id)
                can_edit = current_employee.edit_employee_perm_permission and not is_current_user
                can_delete = current_employee.edit_employee_perm_permission and not is_current_user
                can_change_role = current_employee.edit_employee_perm_permission and not is_current_user

                data = {
                    "employee_name": employee.name,
                    "account_id": employee.account_id,
                    "role": employee.role,
                    "role_display": self._get_role_display_name(employee.role),
                    "created_at": created_at,
                    "publications_count": publications_count,
                    "generations_count": generations_count,
                    "permissions_text": permissions_text,
                    "is_current_user": is_current_user,
                    "can_edit_permissions": can_edit,
                    "can_delete": can_delete,
                    "can_change_role": can_change_role,
                    "current_index": current_index,
                    "total_count": len(all_employee_ids),
                    "has_prev": current_index > 1,
                    "has_next": current_index < len(all_employee_ids),
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
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeGetter.get_permissions_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    selected_account_id
                )

                # Если нет сохраненных изменений, берем текущие значения
                if "temp_permissions" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["temp_permissions"] = {
                        "no_moderation": not employee.required_moderation,
                        "autoposting": employee.autoposting_permission,
                        "add_employee": employee.add_employee_permission,
                        "edit_permissions": employee.edit_employee_perm_permission,
                        "top_up_balance": employee.top_up_balance_permission,
                        "social_networks": employee.sign_up_social_net_permission,
                    }
                    dialog_manager.dialog_data["original_permissions"] = dialog_manager.dialog_data[
                        "temp_permissions"].copy()

                permissions = dialog_manager.dialog_data["temp_permissions"]
                original = dialog_manager.dialog_data["original_permissions"]

                # Проверяем, есть ли изменения
                has_changes = permissions != original

                data = {
                    "employee_name": employee.name,
                    "role": employee.role,
                    "role_display": self._get_role_display_name(employee.role),
                    "no_moderation_icon": "✅" if permissions["no_moderation"] else "❌",
                    "autoposting_icon": "✅" if permissions["autoposting"] else "❌",
                    "add_employee_icon": "✅" if permissions["add_employee"] else "❌",
                    "edit_permissions_icon": "✅" if permissions["edit_permissions"] else "❌",
                    "top_up_balance_icon": "✅" if permissions["top_up_balance"] else "❌",
                    "social_networks_icon": "✅" if permissions["social_networks"] else "❌",
                    "has_changes": has_changes,
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_delete_confirmation_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeGetter.get_delete_confirmation_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    selected_account_id
                )

                data = {
                    "employee_name": employee.name,
                    "account_id": employee.account_id,
                    "role": employee.role,
                    "role_display": self._get_role_display_name(employee.role),
                }

                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

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
