# internal/controller/tg/dialog/change_employee/dialog.py
from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, ScrollingGroup, Select, NumberedPager, Group
from aiogram_dialog.widgets.input import TextInput

from internal import interface, model


class ChangeEmployeeDialog(interface.IChangeEmployeeDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            change_employee_service: interface.IChangeEmployeeDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.change_employee_service = change_employee_service

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_employee_list_window(),
            self.get_employee_detail_window(),
            self.get_change_permissions_window(),
            self.get_confirm_delete_window(),
        )

    def get_employee_list_window(self) -> Window:
        """Окно со списком сотрудников"""
        return Window(
            Multi(
                Const("👥 <b>Управление сотрудниками</b>\n\n"),
                Format("🏢 Организация: <b>{organization_name}</b>\n"),
                Format("👤 Всего сотрудников: <b>{employees_count}</b>\n\n"),
                Case(
                    {
                        True: Const("🔍 <i>Результаты поиска:</i>\n"),
                        False: Const("📋 <i>Выберите сотрудника для управления:</i>"),
                    },
                    selector="has_search"
                ),
                sep="",
            ),

            # Поле поиска
            TextInput(
                id="search_employee",
                on_success=self.change_employee_service.handle_search_employee,
            ),

            # Список сотрудников с прокруткой
            ScrollingGroup(
                Select(
                    Format("👤 {item[name]} ({item[role_display]})"),
                    id="employee_select",
                    items="employees",
                    item_id_getter=lambda item: str(item["account_id"]),
                    on_click=self.change_employee_service.handle_select_employee,
                ),
                id="employee_scroll",
                width=1,
                height=6,
                hide_on_single_page=True,
            ),

            # Пагинация
            NumberedPager(
                scroll="employee_scroll",
                when="show_pager",
            ),

            Row(
                Button(
                    Const("🔄 Обновить"),
                    id="refresh_list",
                    on_click=self.change_employee_service.handle_refresh_list,
                ),
                Button(
                    Case(
                        {
                            True: Const("❌ Очистить поиск"),
                            False: Const(""),
                        },
                        selector="has_search"
                    ),
                    id="clear_search",
                    on_click=self.change_employee_service.handle_clear_search,
                    when="has_search",
                ),
            ),

            Back(Const("◀️ Назад")),

            state=model.ChangeEmployeeStates.employee_list,
            getter=self.change_employee_service.get_employee_list_data,
            parse_mode="HTML",
        )

    def get_employee_detail_window(self) -> Window:
        """Окно с детальной информацией о сотруднике"""
        return Window(
            Multi(
                Const("👤 <b>Информация о сотруднике</b>\n\n"),
                Const("📋 <b>Основные данные:</b>\n"),
                Format("• Имя: <b>{employee_name}</b>\n"),
                Format("• ID аккаунта: <code>{account_id}</code>\n"),
                Format("• Роль: <b>{role_display}</b>\n"),
                Format("• Добавлен: {created_at}\n\n"),

                Const("📊 <b>Статистика:</b>\n"),
                Format("• Публикаций: <b>{publications_count}</b>\n"),
                Format("• Генераций контента: <b>{generations_count}</b>\n\n"),

                Const("⚙️ <b>Текущие разрешения:</b>\n"),
                Format("{permissions_text}\n"),

                Case(
                    {
                        True: Const("\n⚠️ <i>Это ваш аккаунт</i>"),
                        False: Const(""),
                    },
                    selector="is_current_user"
                ),
                sep="",
            ),

            # Навигация между сотрудниками в строку
            Row(
                Button(
                    Const("⬅️"),
                    id="prev_employee",
                    on_click=self.change_employee_service.handle_navigate_employee,
                    when="has_prev",
                ),
                Button(
                    Format("📍 {current_index}/{total_count}"),
                    id="current_position",
                    on_click=None,
                ),
                Button(
                    Const("➡️"),
                    id="next_employee",
                    on_click=self.change_employee_service.handle_navigate_employee,
                    when="has_next",
                ),
            ),

            # Остальные кнопки действий в колонку
            Column(
                Button(
                    Const("✏️ Изменить разрешения"),
                    id="edit_permissions",
                    on_click=lambda c, b, d: d.switch_to(model.ChangeEmployeeStates.change_permissions),
                    when="can_edit_permissions",
                ),
                Button(
                    Const("🔄 Изменить роль"),
                    id="change_role",
                    on_click=self.change_employee_service.handle_show_role_change,
                    when="can_change_role",
                ),
                Button(
                    Const("🗑 Удалить сотрудника"),
                    id="delete_employee",
                    on_click=lambda c, b, d: d.switch_to(model.ChangeEmployeeStates.confirm_delete),
                    when="can_delete",
                ),

                Back(Const("◀️ К списку")),
            ),

            state=model.ChangeEmployeeStates.employee_detail,
            getter=self.change_employee_service.get_employee_detail_data,
            parse_mode="HTML",
        )

    def get_change_permissions_window(self) -> Window:
        """Окно изменения разрешений сотрудника"""
        return Window(
            Multi(
                Const("⚙️ <b>Изменение разрешений</b>\n\n"),
                Format("👤 Сотрудник: <b>{employee_name}</b>\n"),
                Format("🏷 Роль: <b>{role_display}</b>\n\n"),
                Const("📝 <b>Настройка разрешений:</b>\n"),
                Const("<i>Нажмите на правило для включения/выключения</i>\n\n"),

                Case(
                    {
                        True: Const("⚠️ <b>Внимание:</b> есть несохраненные изменения"),
                        False: Const(""),
                    },
                    selector="has_changes"
                ),
                sep="",
            ),

            Column(
                # Разрешения с одной кнопкой на правило
                Button(
                    Format("{no_moderation_icon} Публикации без модерации"),
                    id="toggle_no_moderation",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{autoposting_icon} Авто-постинг"),
                    id="toggle_autoposting",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{add_employee_icon} Добавление сотрудников"),
                    id="toggle_add_employee",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{edit_permissions_icon} Изменение разрешений"),
                    id="toggle_edit_permissions",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{top_up_balance_icon} Пополнение баланса"),
                    id="toggle_top_up_balance",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{social_networks_icon} Подключение соцсетей"),
                    id="toggle_social_networks",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
            ),

            Row(
                Button(
                    Const("💾 Сохранить"),
                    id="save_permissions",
                    on_click=self.change_employee_service.handle_save_permissions,
                    when="has_changes",
                ),
                Button(
                    Const("↩️ Сбросить"),
                    id="reset_permissions",
                    on_click=self.change_employee_service.handle_reset_permissions,
                    when="has_changes",
                ),
                Back(Const("❌ Отмена")),
            ),

            state=model.ChangeEmployeeStates.change_permissions,
            getter=self.change_employee_service.get_permissions_data,
            parse_mode="HTML",
        )

    def get_confirm_delete_window(self) -> Window:
        """Окно подтверждения удаления сотрудника"""
        return Window(
            Multi(
                Const("⚠️ <b>Подтверждение удаления</b>\n\n"),
                Format("Вы действительно хотите удалить сотрудника?\n\n"),
                Format("👤 <b>{employee_name}</b>\n"),
                Format("ID: {account_id}\n"),
                Format("Роль: {role_display}\n\n"),
                Const("❗ <b>Это действие необратимо!</b>\n"),
                Const("Сотрудник потеряет доступ к организации."),
                sep="",
            ),

            Row(
                Button(
                    Const("🗑 Да, удалить"),
                    id="confirm_delete",
                    on_click=self.change_employee_service.handle_delete_employee,
                ),
                Back(Const("❌ Отмена")),
            ),

            state=model.ChangeEmployeeStates.confirm_delete,
            getter=self.change_employee_service.get_delete_confirmation_data,
            parse_mode="HTML",
        )