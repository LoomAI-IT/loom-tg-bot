from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Back, Checkbox
from aiogram_dialog.widgets.input import TextInput
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class AddSocialNetworkDialog(interface.IAddSocialNetworkDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            add_social_network_service: interface.IAddSocialNetworkService,
            add_social_network_getter: interface.IAddSocialNetworkGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.add_social_network_service = add_social_network_service
        self.add_social_network_getter = add_social_network_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_select_network_window(),
            self.get_telegram_main_window(),
            self.get_telegram_connect_window(),
            self.get_telegram_edit_window(),
            self.get_telegram_change_username_window(),
            self.get_vkontakte_setup_window(),
            self.get_youtube_setup_window(),
            self.get_instagram_setup_window(),
        )

    def get_select_network_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Подключение социальных сетей</b> <br><br>"),
                Const("📱 <b>Выберите платформу для подключения или изменения:</b> <br>"),
                Const("💡 <i>Подключенные сети помечены зеленым цветом</i> <br>"),
                Const("🤖 <i>Звездочка (*) означает автовыбор для публикации</i>"),
                sep="",
            ),

            Column(
                Button(
                    Case(
                        {
                            "connected_autoselect": Const("✅ Telegram*"),
                            "connected_no_autoselect": Const("✅ Telegram"),
                            "not_connected": Const("📱 Telegram"),
                        },
                        selector="telegram_status"
                    ),
                    id="select_telegram",
                    on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.telegram_main, ShowMode.EDIT),
                ),
                Button(
                    Case(
                        {
                            "connected_autoselect": Const("✅ ВКонтакте*"),
                            "connected_no_autoselect": Const("✅ ВКонтакте"),
                            "not_connected": Const("🔵 ВКонтакте"),
                        },
                        selector="vkontakte_status"
                    ),
                    id="select_vkontakte",
                    on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.vkontakte_setup, ShowMode.EDIT),
                ),
                Button(
                    Case(
                        {
                            "connected_autoselect": Const("✅ YouTube*"),
                            "connected_no_autoselect": Const("✅ YouTube"),
                            "not_connected": Const("🎥 YouTube"),
                        },
                        selector="youtube_status"
                    ),
                    id="select_youtube",
                    on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.youtube_setup, ShowMode.EDIT),
                ),
                Button(
                    Case(
                        {
                            "connected_autoselect": Const("✅ Instagram*"),
                            "connected_no_autoselect": Const("✅ Instagram"),
                            "not_connected": Const("📷 Instagram"),
                        },
                        selector="instagram_status"
                    ),
                    id="select_instagram",
                    on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.instagram_setup, ShowMode.EDIT),
                ),
            ),

            Button(
                Const("◀️ К управлению организацией"),
                id="go_to_organization_menu",
                on_click=self.add_social_network_service.handle_go_to_organization_menu,
            ),

            state=model.AddSocialNetworkStates.select_network,
            getter=self.add_social_network_getter.get_select_network_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_telegram_main_window(self) -> Window:
        return Window(
            Multi(
                Const("📱 <b>Telegram</b> <br><br>"),
                Case(
                    {
                        True: Multi(
                            Const("✅ <b>Подключен</b> <br><br>"),
                            Format("📣 <b>Канал:</b> @{telegram_channel_username} <br>"),
                            Case(
                                {
                                    True: Const("🤖 <b>Автовыбор:</b> ✅ включен <br>"),
                                    False: Const("🤖 <b>Автовыбор:</b> ❌ выключен <br>"),
                                },
                                selector="telegram_autoselect"
                            ),
                            Const(
                                "<br>💡 <i>Автовыбор означает, что новый контент будет автоматически предназначен для этого канала</i>"),
                        ),
                        False: Multi(
                            Const("❌ <b>Не подключен</b> <br><br>"),
                            Const("📝 <b>Для подключения:</b> <br>"),
                            Const("1️⃣ Создайте канал в Telegram <br>"),
                            Const("2️⃣ Добавьте бота @KonturContentBot в администраторы <br>"),
                            Const("3️⃣ Нажмите кнопку «Подключить» <br><br>"),
                            Const("⚠️ <b>Важно:</b> У канала должен быть публичный username"),
                        ),
                    },
                    selector="telegram_connected"
                ),
                sep="",
            ),

            Column(
                # Кнопки для подключенного канала
                Button(
                    Const("✏️ Изменить"),
                    id="edit_telegram",
                    on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.telegram_edit, ShowMode.EDIT),
                    when="telegram_connected"
                ),
                Button(
                    Const("🗑️ Удалить"),
                    id="delete_telegram",
                    on_click=self.add_social_network_service.handle_disconnect_telegram,
                    when="telegram_connected"
                ),

                # Кнопка для подключения
                Button(
                    Const("🔗 Подключить"),
                    id="connect_telegram",
                    on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.telegram_connect, ShowMode.EDIT),
                    when="telegram_not_connected"
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="go_to_select_category",
                on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.select_network, ShowMode.EDIT),
            ),

            state=model.AddSocialNetworkStates.telegram_main,
            getter=self.add_social_network_getter.get_telegram_main_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_telegram_connect_window(self) -> Window:
        return Window(
            Multi(
                Const("🔗 <b>Подключение telegram канала</b> <br><br>"),

                # Шаг 1: Ввод логина
                Case(
                    {
                        False: Const("📝 <b>Шаг 1:</b> Введите username канала (без @) <br><br>⌨️ <i>Введите username:</i>"),
                        True: Format("✅ <b>Шаг 1:</b> Username введен (@{telegram_channel_username}) <br><br>"),
                    },
                    selector="has_telegram_channel_username"
                ),
                Case(
                    {
                        True: Const("<br><br>❌ <b>Ошибка:</b> Канал не найден или бот не добавлен в администраторы"),
                        False: Const(""),
                    },
                    selector="has_invalid_telegram_permission"
                ),
                # Шаг 2: Автовыбор (показывается только после ввода username)
                Case(
                    {
                        True: Const(
                            "🤖 <b>Шаг 2:</b> Настройка автовыбора <br><br>💡 <i>Если включить автовыбор, новый контент будет автоматически предназначен для этого канала</i>"),
                        False: Const(""),
                    },
                    selector="has_telegram_channel_username"
                ),

                # Ошибки валидации
                Case(
                    {
                        True: Const("<br><br>❌ <b>Ошибка:</b> Username канала не может быть пустым"),
                        False: Const(""),
                    },
                    selector="has_void_telegram_channel_username"
                ),
                Case(
                    {
                        True: Const(
                            "<br><br>❌ <b>Ошибка:</b> Неверный формат username. Используйте латиницу, цифры и подчеркивания (5-32 символа)"),
                        False: Const(""),
                    },
                    selector="has_invalid_telegram_channel_username"
                ),
                sep="",
            ),

            TextInput(
                id="telegram_channel_username_input",
                on_success=self.add_social_network_service.handle_telegram_channel_username_input,
            ),

            Column(
                Checkbox(
                    Const("🤖 Автовыбор включен"),
                    Const("🤖 Включить автовыбор"),
                    id="autoselect_checkbox",
                    default=False,
                    when="has_telegram_channel_username"
                ),

                Button(
                    Const("💾 Подключить канал"),
                    id="save_telegram_connection",
                    on_click=self.add_social_network_service.handle_save_telegram_connection,
                    when="has_telegram_channel_username"
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="go_to_select_category",
                on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.telegram_main, ShowMode.EDIT),
            ),

            state=model.AddSocialNetworkStates.telegram_connect,
            getter=self.add_social_network_getter.get_telegram_connect_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_telegram_edit_window(self) -> Window:
        return Window(
            Multi(
                Const("✏️ <b>Редактирование telegram канала</b> <br><br>"),
                Format("📣 <b>Текущий канал:</b> @{telegram_channel_username} <br>"),
                Case(
                    {
                        True: Format("🆕 <b>Новый канал:</b> @{telegram_channel_username} <br>"),
                        False: Const(""),
                    },
                    selector="has_new_telegram_channel_username"
                ),
                Case(
                    {
                        True: Const("🤖 <b>Автовыбор:</b> ✅ включен <br><br>"),
                        False: Const("🤖 <b>Автовыбор:</b> ❌ выключен <br><br>"),
                    },
                    selector="has_telegram_autoselect"
                ),
                Const("⚙️ <b>Доступные настройки:</b>"),
                sep="",
            ),

            Column(
                # Кнопка изменения логина
                Button(
                    Const("📝 Изменить логин канала"),
                    id="change_telegram_channel_username",
                    on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.telegram_change_username,
                                                         ShowMode.EDIT),
                ),

                # Чекбокс автовыбора с обработчиком изменения
                Checkbox(
                    Const("🤖 Автовыбор включен"),
                    Const("🤖 Включить автовыбор"),
                    id="telegram_autoselect_checkbox",
                    default=False,
                ),

                Button(
                    Const("💾 Сохранить изменения"),
                    id="save_changes",
                    on_click=self.add_social_network_service.handle_save_telegram_changes,
                    when="has_changes"
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="go_to_telegram_main",
                on_click=self.add_social_network_service.handle_back_from_edit,
            ),

            state=model.AddSocialNetworkStates.telegram_edit,
            getter=self.add_social_network_getter.get_telegram_edit_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_telegram_change_username_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Изменение логина Telegram канала</b> <br><br>"),
                Format("📣 <b>Текущий канал:</b> @{telegram_channel_username} <br><br>"),
                Const("⌨️ <b>Введите новый username канала (без @):</b> <br>"),
                Const("💡 <i>Бот должен быть добавлен в администраторы нового канала</i> <br>"),

                # Ошибки валидации
                Case(
                    {
                        True: Const("<br><br>❌ <b>Ошибка:</b> Канал не найден или бот не добавлен в администраторы"),
                        False: Const(""),
                    },
                    selector="has_invalid_telegram_permission"
                ),
                Case(
                    {
                        True: Const("<br><br>❌ <b>Ошибка:</b> Username канала не может быть пустым"),
                        False: Const(""),
                    },
                    selector="has_void_telegram_channel_username"
                ),
                Case(
                    {
                        True: Const(
                            "<br><br>❌ <b>Ошибка:</b> Неверный формат username. Используйте латиницу, цифры и подчеркивания (5-32 символа)"),
                        False: Const(""),
                    },
                    selector="has_invalid_telegram_channel_username"
                ),
                sep="",
            ),

            # Поле ввода нового username
            TextInput(
                id="new_telegram_channel_username_input",
                on_success=self.add_social_network_service.handle_new_telegram_channel_username_input,
            ),

            Button(
                Const("◀️ Назад"),
                id="go_to_select_category",
                on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.telegram_edit, ShowMode.EDIT),
            ),

            state=model.AddSocialNetworkStates.telegram_change_username,
            getter=self.add_social_network_getter.get_telegram_change_username_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_vkontakte_setup_window(self) -> Window:
        return Window(
            Multi(
                Const("🔵 <b>Настройка ВКонтакте</b> <br><br>"),
                Const("🔜 <i>Функционал находится в разработке</i> <br>"),
                Const("📅 <b>Скоро будет доступно:</b> <br>"),
                Const("• Автоматическая публикация в группу <br>"),
                Const("• Настройка времени постинга <br>"),
                Const("• Статистика охватов <br>"),
                Const("• Настройки автовыбора"),
                sep="",
            ),

            Button(
                Const("◀️ Назад"),
                id="go_to_select_category",
                on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.select_network, ShowMode.EDIT),
            ),

            state=model.AddSocialNetworkStates.vkontakte_setup,
            getter=self.add_social_network_getter.get_vkontakte_setup_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_youtube_setup_window(self) -> Window:
        return Window(
            Multi(
                Const("🎥 <b>Настройка YouTube</b> <br><br>"),
                Const("🔜 <i>Функционал находится в разработке</i> <br>"),
                Const("📅 <b>Скоро будет доступно:</b> <br>"),
                Const("• Подключение канала YouTube <br>"),
                Const("• Автоматическая публикация видео <br>"),
                Const("• Настройки автовыбора для видеоконтента <br>"),
                Const("• Управление описаниями и тегами"),
                sep="",
            ),

            Button(
                Const("◀️ Назад"),
                id="go_to_select_category",
                on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.select_network, ShowMode.EDIT),
            ),

            state=model.AddSocialNetworkStates.youtube_setup,
            getter=self.add_social_network_getter.get_youtube_setup_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_instagram_setup_window(self) -> Window:
        return Window(
            Multi(
                Const("📷 <b>Настройка Instagram</b> <br><br>"),
                Const("🔜 <i>Функционал находится в разработке</i> <br>"),
                Const("📅 <b>Скоро будет доступно:</b> <br>"),
                Const("• Подключение бизнес-аккаунта Instagram <br>"),
                Const("• Автоматическая публикация постов и stories <br>"),
                Const("• Настройки автовыбора для визуального контента <br>"),
                Const("• Планирование публикаций"),
                sep="",
            ),

            Button(
                Const("◀️ Назад"),
                id="go_to_select_category",
                on_click=lambda c, b, d: d.switch_to(model.AddSocialNetworkStates.select_network, ShowMode.EDIT),
            ),

            state=model.AddSocialNetworkStates.instagram_setup,
            getter=self.add_social_network_getter.get_instagram_setup_data,
            parse_mode=SULGUK_PARSE_MODE,
        )