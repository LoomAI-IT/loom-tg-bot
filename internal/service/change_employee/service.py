from typing import Any

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ChangeEmployeeService(interface.IChangeEmployeeService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client

    async def handle_select_employee(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            employee_id: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "ChangeEmployeeService.handle_select_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Сохраняем выбранного сотрудника
                dialog_manager.dialog_data["selected_account_id"] = employee_id

                # Очищаем временные данные разрешений
                dialog_manager.dialog_data.pop("temp_permissions", None)
                dialog_manager.dialog_data.pop("original_permissions", None)

                self.logger.info("Выбран сотрудник для редактирования")

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
                "ChangeEmployeeService.handle_search_employee",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Сохраняем поисковый запрос
                dialog_manager.dialog_data["search_query"] = search_query.strip()

                self.logger.info("Поиск сотрудников")

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
                "ChangeEmployeeService.handle_clear_search",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Очищаем поисковый запрос
                dialog_manager.dialog_data.pop("search_query", None)

                self.logger.info("Поиск очищен")

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
                "ChangeEmployeeService.handle_refresh_list",
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
                "ChangeEmployeeService.handle_navigate_employee",
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
                "ChangeEmployeeService.handle_go_to_organization_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.OrganizationMenuStates.organization_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Переход в меню организации")
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
                "ChangeEmployeeService.handle_toggle_permission",
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
                "ChangeEmployeeService.handle_save_permissions",
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
                    await self.bot.send_message(
                        employee_state[0].tg_chat_id,
                        "ℹ️ Ваши разрешения в организации были изменены администратором.\n"
                        "Нажмите /start для обновления информации."
                    )

                self.logger.info("Разрешения сотрудника обновлены")

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
                "ChangeEmployeeService.handle_reset_permissions",
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
                "ChangeEmployeeService.handle_show_role_change",
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
                "ChangeEmployeeService.handle_delete_employee",
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
                        organization_id=0
                    )

                    await self.bot.send_message(
                        employee_state[0].tg_chat_id,
                        "⚠️ Вы были удалены из организации.\n"
                        "Для восстановления доступа обратитесь к администратору."
                    )

                self.logger.info("Сотрудник удален из организации")

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
