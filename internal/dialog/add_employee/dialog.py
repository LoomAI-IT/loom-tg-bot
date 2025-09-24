from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, Select
from aiogram_dialog.widgets.input import TextInput

from internal import interface, model


class AddEmployeeDialog(interface.IAddEmployeeDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            add_employee_service: interface.IAddEmployeeService,
            add_employee_getter: interface.IAddEmployeeGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.add_employee_service = add_employee_service
        self.add_employee_getter = add_employee_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_enter_account_id_window(),
            self.get_enter_name_window(),
            self.get_enter_role_window(),
            self.get_set_permissions_window(),
            self.get_confirm_employee_window(),
        )

    def get_enter_account_id_window(self) -> Window:
        return Window(
            Multi(
                Const("👤 <b>Добавление нового сотрудника</b>\n\n"),
                Const("📝 <b>Шаг 1/4: Введите ID аккаунта сотрудника</b>\n\n"),
                Const("⚠️ <i>Убедитесь, что пользователь уже зарегистрирован в системе</i>\n\n"),

                # Validation error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> ID аккаунта не может быть пустым\n\n"),
                        False: Const(""),
                    },
                    selector="has_void_account_id"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> ID аккаунта должен быть положительным числом\n\n"),
                        False: Const(""),
                    },
                    selector="has_invalid_account_id"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Не удалось обработать ID аккаунта. Попробуйте еще раз\n\n"),
                        False: Const(""),
                    },
                    selector="has_account_id_processing_error"
                ),

                Const("💡 <b>Введите ID аккаунта:</b>\n"),

                # Show entered account ID if valid
                Case(
                    {
                        True: Format("📌 <b>ID аккаунта:</b> {account_id}"),
                        False: Const("💬 Ожидание ввода ID аккаунта..."),
                    },
                    selector="has_account_id"
                ),
                sep="",
            ),

            TextInput(
                id="account_id_input",
                on_success=self.add_employee_service.handle_account_id_input,
            ),

            Row(
                Button(
                    Const("➡️ Далее"),
                    id="next_to_name",
                    on_click=lambda c, b, d: d.switch_to(model.AddEmployeeStates.enter_name, ShowMode.EDIT),
                    when="has_account_id"
                ),
                Button(
                    Const("⬅️ Вернуться в меню организации"),
                    id="go_to_organization_menu",
                    on_click=self.add_employee_service.handle_go_to_organization_menu,
                ),
            ),

            state=model.AddEmployeeStates.enter_account_id,
            getter=self.add_employee_getter.get_enter_account_id_data,
            parse_mode="HTML",
        )

    def get_enter_name_window(self) -> Window:
        return Window(
            Multi(
                Const("👤 <b>Добавление нового сотрудника</b>\n\n"),
                Const("📝 <b>Шаг 2/4: Введите имя сотрудника</b>\n\n"),
                Format("ID Аккаунта: <b>{account_id}</b>\n\n"),

                # Validation error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Имя не может быть пустым\n\n"),
                        False: Const(""),
                    },
                    selector="has_void_name"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Имя должно быть от 2 до 100 символов\n\n"),
                        False: Const(""),
                    },
                    selector="has_invalid_name_length"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Не удалось обработать имя. Попробуйте еще раз\n\n"),
                        False: Const(""),
                    },
                    selector="has_name_processing_error"
                ),

                Const("💡 <b>Введите полное имя сотрудника:</b>\n"),

                # Show entered name if valid
                Case(
                    {
                        True: Format("📌 <b>Имя:</b> {name}"),
                        False: Const("💬 Ожидание ввода имени..."),
                    },
                    selector="has_name"
                ),
                sep="",
            ),

            TextInput(
                id="name_input",
                on_success=self.add_employee_service.handle_name_input,
            ),

            Row(
                Button(
                    Const("➡️ Далее"),
                    id="next_to_role",
                    on_click=lambda c, b, d: d.switch_to(model.AddEmployeeStates.enter_role, ShowMode.EDIT),
                    when="has_name"
                ),
                Back(Const("◀️ Назад")),
            ),

            state=model.AddEmployeeStates.enter_name,
            getter=self.add_employee_getter.get_enter_name_data,
            parse_mode="HTML",
        )

    def get_enter_role_window(self) -> Window:
        return Window(
            Multi(
                Const("👤 <b>Добавление нового сотрудника</b>\n\n"),
                Const("📝 <b>Шаг 3/4: Выберите роль сотрудника</b>\n\n"),
                Format("ID Аккаунта: <b>{account_id}</b>\n"),
                Format("Имя: <b>{name}</b>\n\n"),
                Const("💡 <b>Выберите роль для сотрудника:</b>\n"),

                # Show selected role
                Case(
                    {
                        True: Format("📌 <b>Выбранная роль:</b> {selected_role_display}"),
                        False: Const("💬 Выберите роль из списка ниже..."),
                    },
                    selector="has_selected_role"
                ),
                sep="",
            ),

            Column(
                Select(
                    Format("{item[title]}"),
                    id="role_select",
                    items="roles",
                    item_id_getter=lambda item: item["value"],
                    on_click=self.add_employee_service.handle_role_selection,
                ),
            ),

            Row(
                Button(
                    Const("➡️ Далее"),
                    id="next_to_permissions",
                    on_click=lambda c, b, d: d.switch_to(model.AddEmployeeStates.set_permissions, ShowMode.EDIT),
                    when="has_selected_role"
                ),
                Back(Const("◀️ Назад")),
            ),

            state=model.AddEmployeeStates.enter_role,
            getter=self.add_employee_getter.get_enter_role_data,
            parse_mode="HTML",
        )

    def get_set_permissions_window(self) -> Window:
        return Window(
            Multi(
                Const("👤 <b>Добавление нового сотрудника</b>\n\n"),
                Const("📝 <b>Шаг 4/4: Настройте разрешения сотрудника</b>\n\n"),
                Format("ID Аккаунта: <b>{account_id}</b>\n"),
                Format("Имя: <b>{name}</b>\n"),
                Format("Роль: <b>{role}</b>\n\n"),
                Const("⚙️ <b>Разрешения:</b>\n"),
                Const("<i>Нажмите на разрешение, чтобы включить/выключить его</i>"),
                sep="",
            ),

            Column(
                # Публикации без одобрения
                Button(
                    Format("{required_moderation_icon} Публикации без одобрения"),
                    id="toggle_required_moderation",
                    on_click=self.add_employee_service.handle_toggle_permission,
                ),

                # Включить авто-постинг
                Button(
                    Format("{autoposting_icon} Включить авто-постинг"),
                    id="toggle_autoposting",
                    on_click=self.add_employee_service.handle_toggle_permission,
                ),

                # Добавлять сотрудников
                Button(
                    Format("{add_employee_icon} Добавлять сотрудников"),
                    id="toggle_add_employee",
                    on_click=self.add_employee_service.handle_toggle_permission,
                ),

                # Изменять разрешения сотрудников
                Button(
                    Format("{edit_permissions_icon} Изменять разрешения сотрудников"),
                    id="toggle_edit_permissions",
                    on_click=self.add_employee_service.handle_toggle_permission,
                ),

                # Пополнять баланс
                Button(
                    Format("{top_up_balance_icon} Пополнять баланс"),
                    id="toggle_top_up_balance",
                    on_click=self.add_employee_service.handle_toggle_permission,
                ),

                # Подключать социальные сети
                Button(
                    Format("{sign_up_social_networks_icon} Подключать социальные сети"),
                    id="toggle_sign_up_social_networks",
                    on_click=self.add_employee_service.handle_toggle_permission,
                ),
            ),

            Row(
                Button(
                    Const("➡️ К подтверждению"),
                    id="next_to_confirm",
                    on_click=lambda c, b, d: d.switch_to(model.AddEmployeeStates.confirm_employee, ShowMode.EDIT),
                ),
                Back(Const("◀️ Назад")),
            ),

            state=model.AddEmployeeStates.set_permissions,
            getter=self.add_employee_getter.get_permissions_data,
            parse_mode="HTML",
        )

    def get_confirm_employee_window(self) -> Window:
        return Window(
            Multi(
                Const("👤 <b>Подтверждение создания сотрудника</b>\n\n"),

                # Показываем состояние создания
                Case(
                    {
                        True: Multi(
                            Const("⏳ <b>Создаю сотрудника...</b>\n"),
                            Const("Это может занять время. Пожалуйста, ожидайте."),
                        ),
                        False: Multi(
                            Const("📋 <b>Проверьте введенные данные:</b>\n\n"),
                            Format("ID Аккаунта: <b>{account_id}</b>\n"),
                            Format("Имя: <b>{name}</b>\n"),
                            Format("Роль: <b>{role}</b>\n\n"),
                            Const("⚙️ <b>Разрешения:</b>\n"),
                            Format("{permissions_text}\n\n"),

                            # Показываем ошибки создания если есть
                            Case(
                                {
                                    True: Const(
                                        "⚠️ <b>Ошибка:</b> Не удалось создать сотрудника. Попробуйте еще раз\n\n"),
                                    False: Const(""),
                                },
                                selector="has_creation_error"
                            ),

                            Const("❓ Всё правильно?"),
                        ),
                    },
                    selector="is_creating_employee"
                ),
                sep="",
            ),

            Row(
                Button(
                    Const("✅ Создать сотрудника"),
                    id="create_employee",
                    on_click=self.add_employee_service.handle_create_employee,
                    when="~is_creating_employee",  # Отключаем во время создания
                ),
                Back(
                    Const("✏️ Изменить"),
                    when="~is_creating_employee",  # Отключаем во время создания
                ),
            ),

            state=model.AddEmployeeStates.confirm_employee,
            getter=self.add_employee_getter.get_confirm_data,
            parse_mode="HTML",
        )