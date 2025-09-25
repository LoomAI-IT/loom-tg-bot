from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row

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
                    True: Format("🔄 <b>Восстановление после ошибки</b>\n\n"),
                    False: Const(""),
                },
                selector="show_error_recovery",
            ),
            Format("👋 Привет, {name}! Я буду создавать контент для твоей компании вместе с тобой."),
            Const("Расскажи мне о чём-нибудь текстом или голосом — и начнём ✨"),
            Const("Готов? Жду твоё сообщение! Или воспользуйся кнопками ниже👇"),
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
                )
            ),
            state=model.MainMenuStates.main_menu,
            getter=self.main_menu_getter.get_main_menu_data,
            parse_mode="HTML",
        )
