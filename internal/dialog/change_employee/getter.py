from datetime import datetime

from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ChangeEmployeeGetter(interface.IChangeEmployeeGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.loom_employee_client = loom_employee_client
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client

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
                self.logger.info("Начало загрузки списка сотрудников")

                state = await self._get_state(dialog_manager)
                current_employee = await self.loom_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                organization = await self.loom_organization_client.get_organization_by_id(
                    current_employee.organization_id
                )

                all_employees = await self.loom_employee_client.get_employees_by_organization(
                    organization.id
                )

                search_query = dialog_manager.dialog_data.get("search_query", "")
                if search_query:
                    self.logger.info("Применение фильтрации по поисковому запросу")
                    filtered_employees = [
                        e for e in all_employees
                        if search_query.lower() in e.name.lower()
                    ]
                else:
                    filtered_employees = all_employees

                dialog_manager.dialog_data["all_employee_ids"] = [
                    e.account_id for e in filtered_employees
                ]

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

                self.logger.info("Завершение загрузки списка сотрудников")
                span.set_status(Status(StatusCode.OK))
                return data
            except Exception as err:
                
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
                self.logger.info("Начало загрузки детальной информации о сотруднике")

                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

                state = await self._get_state(dialog_manager)
                current_employee = await self.loom_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                employee = await self.loom_employee_client.get_employee_by_account_id(
                    selected_account_id
                )
                employee_state = (await self.state_repo.state_by_account_id(selected_account_id))[0]

                publications = await self.loom_content_client.get_publications_by_organization(
                    employee.organization_id
                )

                generated_publication_count = 0
                published_publication_count = 0

                rejected_publication_count = 0
                approved_publication_count = 0

                for pub in publications:
                    if pub.moderator_id == employee.account_id:
                        if pub.moderation_status == "approved":
                            approved_publication_count += 1
                        elif pub.moderation_status == "rejected":
                            rejected_publication_count += 1

                    if pub.creator_id == employee.account_id:
                        generated_publication_count += 1

                        if pub.moderation_status == "approved":
                            published_publication_count += 1

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

                permissions_text = "<br>".join(permissions_list)

                all_employee_ids = dialog_manager.dialog_data.get("all_employee_ids", [])
                current_index = all_employee_ids.index(
                    selected_account_id) + 1 if selected_account_id in all_employee_ids else 1

                created_at = employee.created_at
                if isinstance(created_at, str):
                    try:
                        created_date = datetime.fromisoformat(created_at)
                        created_at = created_date.strftime("%d.%m.%Y")
                    except:
                        created_at = "неизвестно"

                is_current_user = (state.account_id == selected_account_id)
                can_edit = current_employee.edit_employee_perm_permission and not is_current_user
                can_delete = current_employee.edit_employee_perm_permission and not is_current_user
                can_change_role = current_employee.edit_employee_perm_permission and not is_current_user

                data = {
                    "employee_name": employee.name,
                    "employee_tg_username": employee_state.tg_username,
                    "account_id": employee.account_id,
                    "role": employee.role,
                    "role_display": self._get_role_display_name(employee.role),
                    "created_at": created_at,
                    "permissions_text": permissions_text,
                    "is_current_user": is_current_user,
                    "can_edit_permissions": can_edit,
                    "can_delete": can_delete,
                    "can_change_role": can_change_role,
                    "current_index": current_index,
                    "total_count": len(all_employee_ids),
                    "has_prev": current_index > 1,
                    "has_next": current_index < len(all_employee_ids),
                    "generated_publication_count": generated_publication_count,
                    "published_publication_count": published_publication_count,
                    "rejected_publication_count": rejected_publication_count,
                    "approved_publication_count": approved_publication_count,
                    "has_moderated_publications": bool(rejected_publication_count or approved_publication_count),
                }

                self.logger.info("Завершение загрузки детальной информации о сотруднике")
                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
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
                self.logger.info("Начало загрузки данных разрешений")

                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

                employee = await self.loom_employee_client.get_employee_by_account_id(
                    selected_account_id
                )

                if "temp_permissions" not in dialog_manager.dialog_data:
                    self.logger.info("Инициализация временных разрешений")
                    dialog_manager.dialog_data["temp_permissions"] = {
                        "required_moderation": employee.required_moderation,
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

                has_changes = permissions != original

                data = {
                    "employee_name": employee.name,
                    "role": employee.role,
                    "role_display": self._get_role_display_name(employee.role),
                    "required_moderation_icon": "✅" if not permissions["required_moderation"] else "❌",
                    "autoposting_icon": "✅" if permissions["autoposting"] else "❌",
                    "add_employee_icon": "✅" if permissions["add_employee"] else "❌",
                    "edit_permissions_icon": "✅" if permissions["edit_permissions"] else "❌",
                    "top_up_balance_icon": "✅" if permissions["top_up_balance"] else "❌",
                    "social_networks_icon": "✅" if permissions["social_networks"] else "❌",
                    "has_changes": has_changes,
                }

                self.logger.info("Завершение загрузки данных разрешений")
                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
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
                self.logger.info("Начало загрузки данных подтверждения удаления")

                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

                employee = await self.loom_employee_client.get_employee_by_account_id(
                    selected_account_id
                )

                data = {
                    "employee_name": employee.name,
                    "account_id": employee.account_id,
                    "role": employee.role,
                    "role_display": self._get_role_display_name(employee.role),
                }

                self.logger.info("Завершение загрузки данных подтверждения удаления")
                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_role_change_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeGetter.get_role_change_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало загрузки данных изменения роли")

                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))
                selected_new_role = dialog_manager.dialog_data.get("selected_new_role")

                employee = await self.loom_employee_client.get_employee_by_account_id(
                    selected_account_id
                )

                state = await self._get_state(dialog_manager)
                current_employee = await self.loom_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                available_roles = self._get_available_roles_for_assignment(
                    current_user_role=current_employee.role,
                    target_employee_role=employee.role
                )

                has_selected_role = selected_new_role is not None
                show_role_list = not has_selected_role

                data = {
                    "employee_name": employee.name,
                    "current_role": employee.role,
                    "current_role_display": self._get_role_display_name(employee.role),
                    "available_roles": available_roles,
                    "has_selected_role": has_selected_role,
                    "show_role_list": show_role_list,
                }

                if selected_new_role:
                    self.logger.info("Роль выбрана, добавление информации о выбранной роли")
                    data.update({
                        "selected_role": selected_new_role,
                        "selected_role_display": self._get_role_display_name(selected_new_role),
                    })

                self.logger.info("Завершение загрузки данных изменения роли")
                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    def _get_available_roles_for_assignment(self, current_user_role: str, target_employee_role: str) -> list[dict]:
        all_roles = {
            "employee": {"role": "employee", "display_name": "Сотрудник"},
            "moderator": {"role": "moderator", "display_name": "Модератор"},
            "admin": {"role": "admin", "display_name": "Администратор"},
            "owner": {"role": "owner", "display_name": "Владелец"},
        }

        available_roles = []

        if current_user_role == "owner":
            available_roles = [all_roles[role] for role in ["employee", "moderator", "admin"]]
        elif current_user_role == "admin":
            available_roles = [all_roles[role] for role in ["employee", "moderator"]]
        elif current_user_role == "moderator":
            available_roles = [all_roles["employee"]]

        # Исключаем текущую роль из доступных
        available_roles = [role for role in available_roles if role["role"] != target_employee_role]

        return available_roles

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
