from aiogram import F
from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.text import Const, Format, Case, Multi
from aiogram_dialog.widgets.kbd import Button, Column, Row
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class MainMenuDialog(interface.IMainMenuDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            main_menu_service: interface.IMainMenuService,
            main_menu_getter: interface.IMainMenuGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.main_menu_service = main_menu_service
        self.main_menu_getter = main_menu_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_main_menu_window(),
        )

    def get_main_menu_window(self) -> Window:
        return Window(
            Case(
                {
                    False: Multi(
                        Case(
                            {
                                True: Format("🔄 <b>Восстановление после ошибки</b> <br><br>"),
                                False: Const(""),
                            },
                            selector="show_error_recovery",
                        ),
                        Format("👋 Привет, {name}! Я буду создавать контент для твоей компании вместе с тобой. <br><br>"),
                        Const("Расскажи мне о чём-нибудь текстом или голосом — и начнём ✨ <br><br>"),
                        Const("Готов? Жду твоё сообщение! Или воспользуйся кнопками ниже👇 <br><br>"),
                        # Text input error messages
                        Case(
                            {
                                True: Const("<br><br>❌ <b>Ошибка:</b> Текст не может быть пустым"),
                                False: Const(""),
                            },
                            selector="has_void_input_text"
                        ),
                        Case(
                            {
                                True: Const("<br><br>📏 <b>Слишком короткий текст</b>\n<i>Минимум 10 символов</i>"),
                                False: Const(""),
                            },
                            selector="has_small_input_text"
                        ),
                        Case(
                            {
                                True: Const("<br><br>📏 <b>Слишком длинный текст</b>\n<i>Максимум 2000 символов</i>"),
                                False: Const(""),
                            },
                            selector="has_big_input_text"
                        ),
                        # Voice input error messages
                        Case(
                            {
                                True: Const(
                                    "<br><br>🎤 <b>Неверный формат</b>\n<i>Отправьте голосовое сообщение или аудиофайл</i>"),
                                False: Const(""),
                            },
                            selector="has_invalid_voice_type"
                        ),
                        Case(
                            {
                                True: Const("<br><br>⏱️ <b>Слишком длинное сообщение</b>\n<i>Максимум 5 минут</i>"),
                                False: Const(""),
                            },
                            selector="has_long_voice_duration"
                        ),
                        Case(
                            {
                                True: Const(
                                    "<br><br>🔍 <b>Не удалось распознать речь</b>\n<i>Попробуйте записать заново или введите текст</i>"),
                                False: Const(""),
                            },
                            selector="has_empty_voice_text"
                        ),
                        Case(
                            {
                                True: Const("<br><br>❌ <b>Ошибка:</b> <i>Неверная ссылка на YouTube</i>"),
                                False: Const(""),
                            },
                            selector="has_invalid_youtube_url"
                        ),
                    ),
                    True: Const("🔄 Распознавание речи...")
                },
                selector="voice_transcribe"
            ),
            Column(
                Row(
                    Button(
                        Const("👨‍💼 Личный кабинет"),
                        id="personal_profile",
                        on_click=self.main_menu_service.handle_go_to_personal_profile,
                    ),
                    Button(
                        Const("🏢 Организация"),
                        id="organization",
                        on_click=self.main_menu_service.handle_go_to_organization,
                    ),
                ),

                Button(
                    Const("📝 Контент"),
                    id="content_generation",
                    on_click=self.main_menu_service.handle_go_to_content,
                ),
                when=~F["voice_transcribe"]
            ),
            TextInput(
                id="text_input",
                on_success=self.main_menu_service.handle_text_input,
            ),

            MessageInput(
                func=self.main_menu_service.handle_voice_input,
                content_types=["voice", "audio"],
            ),

            state=model.MainMenuStates.main_menu,
            getter=self.main_menu_getter.get_main_menu_data,
            parse_mode=SULGUK_PARSE_MODE,
        )
