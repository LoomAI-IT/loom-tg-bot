from typing import Any
from datetime import datetime

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class ChangeEmployeeDialogService(interface.IChangeEmployeeDialogService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_organization_client: interface.IKonturOrganizationClient,
            kontur_publication_client: interface.IKonturPublicationClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_organization_client = kontur_organization_client
        self.kontur_publication_client = kontur_publication_client

    async def get_employee_list_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.get_employee_list_data",
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

                self.logger.info(
                    "Список сотрудников загружен",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: self._get_chat_id(dialog_manager),
                        "organization_id": organization.id,
                        "employees_count": len(all_employees),
                        "filtered_count": len(filtered_employees),
                    }
                )

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
                "ChangeEmployeeDialogService.get_employee_detail_data",
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
                publications_count = 0  # TODO: await self.kontur_publication_client.get_publications_count(selected_account_id)
                generations_count = 0  # TODO: await self.kontur_publication_client.get_generations_count(selected_account_id)

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
                "ChangeEmployeeDialogService.get_permissions_data",
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
                "ChangeEmployeeDialogService.get_delete_confirmation_data",
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

    async def handle_select_employee(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            employee_id: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_select_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Сохраняем выбранного сотрудника
                dialog_manager.dialog_data["selected_account_id"] = employee_id

                # Очищаем временные данные разрешений
                dialog_manager.dialog_data.pop("temp_permissions", None)
                dialog_manager.dialog_data.pop("original_permissions", None)

                self.logger.info(
                    "Выбран сотрудник для редактирования",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "selected_account_id": employee_id,
                    }
                )

                # Переходим к деталям
                await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_detail)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при выборе сотрудника", show_alert=True)
                raise

    async def handle_search_employee(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            search_query: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_search_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Сохраняем поисковый запрос
                dialog_manager.dialog_data["search_query"] = search_query.strip()

                self.logger.info(
                    "Поиск сотрудников",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "search_query": search_query,
                    }
                )

                # Обновляем окно
                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_clear_search(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_clear_search",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Очищаем поисковый запрос
                dialog_manager.dialog_data.pop("search_query", None)

                self.logger.info(
                    "Поиск очищен",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )

                await callback.answer("🔄 Поиск очищен")
                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_refresh_list(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_refresh_list",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Обновляем список
                await dialog_manager.update(dialog_manager.dialog_data)
                await callback.answer("🔄 Список обновлен")

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_navigate_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_navigate_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                button_id = button.widget_id
                all_employee_ids = dialog_manager.dialog_data.get("all_employee_ids", [])
                current_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

                if not all_employee_ids or current_account_id not in all_employee_ids:
                    await callback.answer("❌ Ошибка навигации", show_alert=True)
                    return

                current_index = all_employee_ids.index(current_account_id)

                if button_id == "prev_employee" and current_index > 0:
                    new_account_id = all_employee_ids[current_index - 1]
                elif button_id == "next_employee" and current_index < len(all_employee_ids) - 1:
                    new_account_id = all_employee_ids[current_index + 1]
                else:
                    return

                # Обновляем выбранного сотрудника
                dialog_manager.dialog_data["selected_account_id"] = new_account_id

                # Очищаем временные данные разрешений
                dialog_manager.dialog_data.pop("temp_permissions", None)
                dialog_manager.dialog_data.pop("original_permissions", None)

                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise
    async def handle_go_to_organization_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_go_to_organization_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.OrganizationMenuStates.organization_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info(
                    "Переход в меню организации",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                    }
                )
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
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_toggle_permission",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                button_id = button.widget_id

                # Мапинг кнопок на ключи разрешений
                permission_map = {
                    "toggle_no_moderation": "no_moderation",
                    "toggle_autoposting": "autoposting",
                    "toggle_add_employee": "add_employee",
                    "toggle_edit_permissions": "edit_permissions",
                    "toggle_top_up_balance": "top_up_balance",
                    "toggle_social_networks": "social_networks",
                }

                permission_key = permission_map.get(button_id)
                if not permission_key:
                    return

                # Получаем временные разрешения
                permissions = dialog_manager.dialog_data.get("temp_permissions", {})

                # Переключаем значение
                permissions[permission_key] = not permissions.get(permission_key, False)
                dialog_manager.dialog_data["temp_permissions"] = permissions

                # Названия разрешений для уведомления
                permission_names = {
                    "no_moderation": "Публикации без модерации",
                    "autoposting": "Авто-постинг",
                    "add_employee": "Добавление сотрудников",
                    "edit_permissions": "Изменение разрешений",
                    "top_up_balance": "Пополнение баланса",
                    "social_networks": "Подключение соцсетей",
                }

                status = "включено" if permissions[permission_key] else "выключено"
                permission_name = permission_names.get(permission_key, "Разрешение")

                await callback.answer(f"{permission_name}: {status}")
                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при изменении разрешения", show_alert=True)
                raise

    async def handle_save_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_save_permissions",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))
                permissions = dialog_manager.dialog_data.get("temp_permissions", {})

                # Обновляем разрешения через API
                await self.kontur_employee_client.update_employee_permissions(
                    account_id=selected_account_id,
                    required_moderation=not permissions.get("no_moderation", False),
                    autoposting_permission=permissions.get("autoposting", False),
                    add_employee_permission=permissions.get("add_employee", False),
                    edit_employee_perm_permission=permissions.get("edit_permissions", False),
                    top_up_balance_permission=permissions.get("top_up_balance", False),
                    sign_up_social_net_permission=permissions.get("social_networks", False),
                )

                # Уведомляем сотрудника об изменении прав
                employee_state = await self.state_repo.state_by_account_id(selected_account_id)
                if employee_state:
                    try:
                        await self.bot.send_message(
                            employee_state[0].tg_chat_id,
                            "ℹ️ Ваши разрешения в организации были изменены администратором.\n"
                            "Нажмите /start для обновления информации."
                        )
                    except Exception as notify_err:
                        self.logger.warning(
                            "Не удалось отправить уведомление сотруднику",
                            {
                                "account_id": selected_account_id,
                                "error": str(notify_err),
                            }
                        )

                self.logger.info(
                    "Разрешения сотрудника обновлены",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "employee_account_id": selected_account_id,
                        "permissions": permissions,
                    }
                )

                # Очищаем временные данные
                dialog_manager.dialog_data.pop("temp_permissions", None)
                dialog_manager.dialog_data.pop("original_permissions", None)

                await callback.answer("✅ Разрешения успешно сохранены!", show_alert=True)

                # Возвращаемся к деталям сотрудника
                await dialog_manager.switch_to(model.ChangeEmployeeStates.employee_detail)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при сохранении разрешений", show_alert=True)
                raise

    async def handle_reset_permissions(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_reset_permissions",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Восстанавливаем оригинальные значения
                original = dialog_manager.dialog_data.get("original_permissions", {})
                dialog_manager.dialog_data["temp_permissions"] = original.copy()

                await callback.answer("↩️ Изменения отменены")
                await dialog_manager.update(dialog_manager.dialog_data)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_show_role_change(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_show_role_change",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # TODO: Реализовать диалог изменения роли
                await callback.answer("🚧 Функция изменения роли в разработке", show_alert=True)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_delete_employee(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeDialogService.handle_delete_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                selected_account_id = int(dialog_manager.dialog_data.get("selected_account_id"))

                # Получаем данные удаляемого сотрудника для логирования
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    selected_account_id
                )

                # Удаляем сотрудника из организации
                await self.kontur_employee_client.delete_employee(selected_account_id)

                # Обновляем состояние удаленного сотрудника
                employee_state = await self.state_repo.state_by_account_id(selected_account_id)
                if employee_state:
                    await self.state_repo.change_user_state(
                        employee_state[0].id,
                        organization_id=0  # Убираем доступ к организации
                    )

                    # Уведомляем удаленного сотрудника
                    try:
                        await self.bot.send_message(
                            employee_state[0].tg_chat_id,
                            "⚠️ Вы были удалены из организации.\n"
                            "Для восстановления доступа обратитесь к администратору."
                        )
                    except Exception as notify_err:
                        self.logger.warning(
                            "Не удалось отправить уведомление удаленному сотруднику",
                            {
                                "account_id": selected_account_id,
                                "error": str(notify_err),
                            }
                        )

                self.logger.info(
                    "Сотрудник удален из организации",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: callback.message.chat.id,
                        "deleted_employee_name": employee.name,
                        "deleted_account_id": selected_account_id,
                    }
                )

                await callback.answer(
                    f"✅ Сотрудник {employee.name} успешно удален",
                    show_alert=True
                )

                # Очищаем выбранного сотрудника
                dialog_manager.dialog_data.pop("selected_account_id", None)
                dialog_manager.dialog_data.pop("temp_permissions", None)
                dialog_manager.dialog_data.pop("original_permissions", None)

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
        """Обработка пагинации - устаревший метод, заменен на handle_navigate_employee"""
        await self.handle_navigate_employee(callback, button, dialog_manager)

    # Вспомогательные методы

    def _get_role_display_name(self, role: str) -> str:
        """Получить отображаемое название роли"""
        role_names = {
            "employee": "Сотрудник",
            "moderator": "Модератор",
            "admin": "Администратор",
            "owner": "Владелец",
        }
        return role_names.get(role, role.capitalize())

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        """Получить состояние текущего пользователя"""
        chat_id = self._get_chat_id(dialog_manager)
        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]

    def _get_chat_id(self, dialog_manager: DialogManager) -> int:
        """Получить chat_id из dialog_manager"""
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            return dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            return dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")