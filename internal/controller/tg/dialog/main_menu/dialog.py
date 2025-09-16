# internal/controller/tg/dialog/main_menu/dialog.py
from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back

from internal import interface, model


class MainMenuDialog(interface.IMainMenuDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            main_menu_service: interface.IMainMenuDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.main_menu_service = main_menu_service
        self._dialog = None

    def get_dialog(self) -> Dialog:
        if self._dialog is None:
            self._dialog = Dialog(
                self.get_main_menu_window(),
            )
        return self._dialog

    def get_main_menu_window(self) -> Window:
        return Window(
            Format("🎉 <b>Добро пожаловать, {name}!</b>\n\n"),
            Format("🏢 Я помогу тебе быстро создать и опубликовать пост с помощью искусственного интеллекта. </b>\n"),
            Format("💰 Просто отправь текст или голосовое сообщение — и начнём магию! ✨</b>\n\n"),
            Format("🤖 Я помогу вам создавать и публиковать контент с помощью ИИ.\n"),
            Format("Для создания коротких видео отправь ссылку на YouTube-видео\n\n"),
            Format("👇 Готов? Тогда жду твоего сообщения! 👇"),

            Column(
                Row(
                    Button(
                        Const("👤 Личный кабинет"),
                        id="personal_profile",
                        on_click=self.main_menu_service.handle_go_to_personal_profile,
                    ),
                    Button(
                        Const("📰 Организация"),
                        id="organization",
                        on_click=self.main_menu_service.handle_go_to_organization,
                    ),
                ),
                Button(
                    Const("✍️ Контент"),
                    id="content_generation",
                    on_click=self.main_menu_service.handle_go_to_content,
                ),
            ),
            state=model.MainMenuStates.main_menu,
            getter=self.main_menu_service.get_main_menu_data,
            parse_mode="HTML",
        )
