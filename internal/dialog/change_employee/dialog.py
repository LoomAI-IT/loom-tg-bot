from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, ScrollingGroup, Select, NumberedPager
from aiogram_dialog.widgets.input import TextInput
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class ChangeEmployeeDialog(interface.IChangeEmployeeDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            change_employee_service: interface.IChangeEmployeeService,
            change_employee_getter: interface.IChangeEmployeeGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.change_employee_service = change_employee_service
        self.change_employee_getter = change_employee_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_employee_list_window(),
            self.get_employee_detail_window(),
            self.get_change_permissions_window(),
            self.get_confirm_delete_window(),
            self.get_change_role_window()
        )

    def get_employee_list_window(self) -> Window:
        return Window(
            Multi(
                Const("👥 <b>Управление командой</b><br><br>"),
                Format("🏢 <b>Организация:</b> {organization_name}<br>"),
                Format("👤 <b>Всего сотрудников:</b> {employees_count}<br><br>"),
                Case(
                    {
                        True: Const("🔍 <b>Результаты поиска:</b><br>"),
                        False: Const("📋 <b>Выберите сотрудника для управления:</b>"),
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
                    Format("👤 {item[name]} • {item[role_display]}"),
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
                    Const("🔄 Обновить список"),
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

            Button(
                Const("◀️ Меню организации"),
                id="go_to_organization_menu",
                on_click=self.change_employee_service.handle_go_to_organization_menu,
            ),

            state=model.ChangeEmployeeStates.employee_list,
            getter=self.change_employee_getter.get_employee_list_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_employee_detail_window(self) -> Window:
        return Window(
            Multi(
                Const("👤 <b>Профиль сотрудника</b><br><br>"),
                Const("📋 <b>Основная информация:</b><br>"),
                Format("• <b>Имя:</b> {employee_name}<br>"),
                Format("• <b>Телеграм аккаунт:</b> @{employee_tg_username}<br>"),
                Format("• <b>ID аккаунта:</b> <code>{account_id}</code><br>"),
                Format("• <b>Роль:</b> {role_display}<br>"),
                Format("• <b>В команде с:</b> {created_at}<br><br>"),

                Const("📊 <b>Активность:</b><br>"),
                Format("• <b>Сгенерировано публикаций:</b> {generated_publication_count}<br>"),
                Format("• <b>Опубликовано публикаций:</b> {published_publication_count}<br>"),
                Case(
                    {
                        True: Multi(
                            Format("• <b>Отклонено в ходе модерации:</b> {rejected_publication_count}"),
                            Format("• <b>Опубликовано в ходе модерации:</b> {approved_publication_count}<br><br>"),
                        ),
                        False: Const("")
                    },
                    selector="has_moderated_publications"
                ),

                Const("🔐 <b>Права доступа:</b><br>"),
                Format("{permissions_text}<br>"),

                Case(
                    {
                        True: Const("<br>👆 <i>Это ваш профиль</i>"),
                        False: Const(""),
                    },
                    selector="is_current_user"
                ),
                sep="",
            ),

            Row(
                Button(
                    Const("⬅️"),
                    id="prev_employee",
                    on_click=self.change_employee_service.handle_navigate_employee,
                    when="has_prev",
                ),
                Button(
                    Format("📍 {current_index} из {total_count}"),
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

            Column(
                Button(
                    Const("⚙️ Настроить права"),
                    id="edit_permissions",
                    on_click=lambda c, b, d: d.switch_to(model.ChangeEmployeeStates.change_permissions),
                    when="can_edit_permissions",
                ),
                Button(
                    Const("🔄 Сменить роль"),
                    id="change_role",
                    on_click=self.change_employee_service.handle_show_role_change,
                    when="can_change_role",
                ),
                Button(
                    Const("🗑️ Исключить из команды"),
                    id="delete_employee",
                    on_click=lambda c, b, d: d.switch_to(model.ChangeEmployeeStates.confirm_delete),
                    when="can_delete",
                ),

                Back(Const("◀️ К списку команды")),
            ),

            state=model.ChangeEmployeeStates.employee_detail,
            getter=self.change_employee_getter.get_employee_detail_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_change_permissions_window(self) -> Window:
        return Window(
            Multi(
                Const("⚙️ <b>Настройка прав доступа</b><br><br>"),
                Format("👤 <b>Сотрудник:</b> {employee_name}<br>"),
                Format("🏷️ <b>Роль:</b> {role_display}<br><br>"),
                Const("🔐 <b>Управление правами:</b><br>"),
                Const("💡 <i>Нажмите на право для включения/отключения</i><br><br>"),

                Case(
                    {
                        True: Const("⚠️ <b>Есть несохраненные изменения</b><br>"),
                        False: Const(""),
                    },
                    selector="has_changes"
                ),
                sep="",
            ),

            Column(
                Button(
                    Format("{required_moderation_icon} Публикация без модерации"),
                    id="toggle_required_moderation",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{autoposting_icon} Автоматический постинг"),
                    id="toggle_autoposting",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{add_employee_icon} Приглашение сотрудников"),
                    id="toggle_add_employee",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{edit_permissions_icon} Управление правами доступа"),
                    id="toggle_edit_permissions",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{top_up_balance_icon} Пополнение баланса организации"),
                    id="toggle_top_up_balance",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
                Button(
                    Format("{social_networks_icon} Управление соцсетями"),
                    id="toggle_social_networks",
                    on_click=self.change_employee_service.handle_toggle_permission,
                ),
            ),

            Row(
                Button(
                    Const("💾 Сохранить изменения"),
                    id="save_permissions",
                    on_click=self.change_employee_service.handle_save_permissions,
                    when="has_changes",
                ),
                Button(
                    Const("🔄 Сбросить изменения"),
                    id="reset_permissions",
                    on_click=self.change_employee_service.handle_reset_permissions,
                    when="has_changes",
                ),
                Back(Const("❌ Отменить")),
            ),

            state=model.ChangeEmployeeStates.change_permissions,
            getter=self.change_employee_getter.get_permissions_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_change_role_window(self) -> Window:
        """Единое окно для выбора и подтверждения изменения роли"""
        return Window(
            Multi(
                Const("🔄 <b>Изменение роли сотрудника</b><br><br>"),
                Format("👤 Сотрудник: <b>{employee_name}</b><br>"),
                Format("🏷 Текущая роль: <b>{current_role_display}</b><br><br>"),

                # Показываем разные блоки в зависимости от того, выбрана ли роль
                Case(
                    {
                        True: Multi(
                            Const("✅ <b>Выбранная роль:</b><br>"),
                            Format("🔄 Новая роль: <b>{selected_role_display}</b><br><br>"),
                            Const("ℹ️ <b>Внимание:</b><br>"),
                            Const("• Изменение роли может повлиять на разрешения сотрудника<br>"),
                            Const("• Сотрудник получит уведомление об изменении<br>"),
                            Const("• Это действие можно будет отменить позже<br><br>"),
                            Const("❓ <b>Подтвердить изменение роли?</b>"),
                            sep="",
                        ),
                        False: Multi(
                            Const("📋 <b>Выберите новую роль:</b><br>"),
                            Const("<i>Доступные роли для назначения:</i><br>"),
                            sep="",
                        ),
                    },
                    selector="has_selected_role"
                ),
                sep="",
            ),

            # Список ролей (показывается только если роль не выбрана)
            Column(
                Select(
                    Format("🔹 {item[display_name]}"),
                    id="role_select",
                    items="available_roles",
                    item_id_getter=lambda item: item["role"],
                    on_click=self.change_employee_service.handle_select_role,
                ),
                when="show_role_list",
            ),

            # Кнопки подтверждения (показываются только если роль выбрана)
            Row(
                Button(
                    Const("✅ Да, изменить роль"),
                    id="confirm_role_change",
                    on_click=self.change_employee_service.handle_confirm_role_change,
                    when="has_selected_role",
                ),
                Button(
                    Const("↩️ Выбрать другую"),
                    id="reset_role_selection",
                    on_click=self.change_employee_service.handle_reset_role_selection,
                    when="has_selected_role",
                ),
                when="has_selected_role",
            ),

            # Кнопка отмены (всегда видна)
            Back(Const("❌ Отмена")),

            state=model.ChangeEmployeeStates.change_role,
            getter=self.change_employee_getter.get_role_change_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_confirm_delete_window(self) -> Window:
        return Window(
            Multi(
                Const("⚠️ <b>Подтверждение исключения</b><br><br>"),
                Format("Вы уверены, что хотите исключить сотрудника из команды?<br><br>"),
                Format("👤 <b>Имя:</b> {employee_name}<br>"),
                Format("🆔 <b>ID:</b> <code>{account_id}</code><br>"),
                Format("🏷️ <b>Роль:</b> {role_display}<br><br>"),
                Const("🚨 <b>Внимание:</b> <i>Действие необратимо!</i><br>"),
                Const("Сотрудник потеряет доступ к организации и всем её ресурсам."),
                sep="",
            ),

            Row(
                Button(
                    Const("🗑️ Исключить из команды"),
                    id="confirm_delete",
                    on_click=self.change_employee_service.handle_delete_employee,
                ),
                Back(Const("❌ Отменить")),
            ),

            state=model.ChangeEmployeeStates.confirm_delete,
            getter=self.change_employee_getter.get_delete_confirmation_data,
            parse_mode=SULGUK_PARSE_MODE,
        )