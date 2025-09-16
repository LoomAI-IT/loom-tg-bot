from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, ScrollingGroup, Select, NumberedPager
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
        )

    def get_employee_list_window(self) -> Window:
        """Окно со списком сотрудников"""
        return Window(
            Const("👥 <b>Сотрудники:</b>\n"),
            Format("{employees_count} сотрудников в организации\n"),

            # Поиск по username
            TextInput(
                id="search_employee",
                on_success=self.change_employee_service.handle_search_employee,
            ),

            # Список сотрудников с пагинацией
            ScrollingGroup(
                Select(
                    Format("{item[name]}"),
                    id="employee_select",
                    items="employees",
                    item_id_getter=lambda item: item["id"],
                    on_click=self.change_employee_service.handle_select_employee,
                ),
                id="employee_scroll",
                width=1,
                height=5,
            ),

            # Пагинация
            NumberedPager(
                scroll="employee_scroll",
            ),

            Button(
                Const("🔄 Обновить список"),
                id="refresh_list",
                on_click=self.change_employee_service.handle_pagination,
            ),

            Back(Const("◀️ Назад")),

            state=model.ChangeEmployeeStates.employee_list,
            getter=self.change_employee_service.get_employee_list_data,
            parse_mode="HTML",
        )

    def get_employee_detail_window(self) -> Window:
        """Окно с деталями сотрудника"""
        return Window(
            Multi(
                Const("👤 <b>Сотрудник:</b>\n"),
                Format("{username}\n"),
                Format("Количество публикаций: {publications_count}\n"),
                Format("Количество генераций: {generations_count}\n\n"),
                Const("⚙️ <b>Разрешения пользователя:</b>\n"),
                Format("{permissions_text}"),
                sep="\n",
            ),

            Column(
                Row(
                    Button(
                        Const("◀️"),
                        id="prev_employee",
                        on_click=self.change_employee_service.handle_pagination,
                    ),
                    Button(
                        Format("{username}"),
                        id="current_employee",
                        on_click=None,  # Неактивная кнопка
                    ),
                    Button(
                        Const("▶️"),
                        id="next_employee",
                        on_click=self.change_employee_service.handle_pagination,
                    ),
                ),
                Button(
                    Const("✏️ Изменить разрешения"),
                    id="edit_permissions",
                    on_click=lambda c, b, d: d.switch_to(model.ChangeEmployeeStates.change_permissions),
                ),
                Button(
                    Const("🗑 Удалить сотрудника"),
                    id="delete_employee",
                    on_click=self.change_employee_service.handle_delete_employee,
                ),
                Back(Const("◀️ Назад к списку")),
            ),

            state=model.ChangeEmployeeStates.employee_detail,
            getter=self.change_employee_service.get_employee_detail_data,
            parse_mode="HTML",
        )

    def get_change_permissions_window(self) -> Window:
        """Окно изменения разрешений сотрудника"""
        return Window(
            Multi(
                Format("👤 <b>{username}</b>\n"),
                Const("Количество публикаций: "),
                Format("{publications_count}\n"),
                Const("Количество генераций: "),
                Format("{generations_count}\n\n"),
                Const("⚙️ <b>Разрешения пользователя:</b>\n"),
                sep="",
            ),

            Column(
                # Публикации без одобрения
                Row(
                    Button(
                        Format("{no_moderation_icon}"),
                        id="toggle_no_moderation",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                    Button(
                        Const("Публикации без одобрения"),
                        id="no_moderation_label",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                ),

                # Включить авто-постинг
                Row(
                    Button(
                        Format("{autoposting_icon}"),
                        id="toggle_autoposting",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                    Button(
                        Const("Включить авто-постинг"),
                        id="autoposting_label",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                ),

                # Добавлять сотрудников
                Row(
                    Button(
                        Format("{add_employee_icon}"),
                        id="toggle_add_employee",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                    Button(
                        Const("Добавлять сотрудников"),
                        id="add_employee_label",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                ),

                # Изменять разрешения сотрудников
                Row(
                    Button(
                        Format("{edit_permissions_icon}"),
                        id="toggle_edit_permissions",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                    Button(
                        Const("Изменять разрешения сотрудников"),
                        id="edit_permissions_label",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                ),

                # Пополнять баланс
                Row(
                    Button(
                        Format("{top_up_balance_icon}"),
                        id="toggle_top_up_balance",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                    Button(
                        Const("Пополнять баланс"),
                        id="top_up_balance_label",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                ),

                # Подключать социальные сети
                Row(
                    Button(
                        Format("{social_networks_icon}"),
                        id="toggle_social_networks",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                    Button(
                        Const("Подключать социальные сети"),
                        id="social_networks_label",
                        on_click=self.change_employee_service.handle_toggle_permission,
                    ),
                ),
            ),

            Row(
                Button(
                    Const("💾 Сохранить"),
                    id="save_permissions",
                    on_click=self.change_employee_service.handle_save_permissions,
                ),
                Back(Const("❌ Отмена")),
            ),

            state=model.ChangeEmployeeStates.change_permissions,
            getter=self.change_employee_service.get_permissions_data,
            parse_mode="HTML",
        )
