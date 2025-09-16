from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back

from internal import interface, model


class PersonalProfileDialog(interface.IPersonalProfileDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            personal_profile_service: interface.IPersonalProfileDialog,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.personal_profile_service = personal_profile_service
        self._dialog = None

    def get_dialog(self) -> Dialog:
        if self._dialog is None:
            self._dialog = Dialog(
                self.get_main_menu_window(),
            )
        return self._dialog

    def get_personal_profile_window(self) -> Window:
        return Window(
            Format("👤 <b>Ваш профиль</b>\n\n"),
            Format("Ваше имя: <b>{name}</b>\n"),
            Format("Название организации: <b>{organization_name}</b>\n"),
            Format("Кол-во публикаций: <b>{publications_count}</b>\n"),
            Format("Кол-во генераций: <b>{generations_count}</b>\n\n"),
            Format("Ваши разрешения:\n{permissions_list}\n\n"),

            Column(
                Row(
                    Button(
                        Const("F.A.Q"),
                        id="faq",
                        on_click=self.personal_profile_service.handle_go_to_personal_profile,
                    ),
                    Button(
                        Const("📰 Организация"),
                        id="publications",
                        on_click=self.personal_profile_service.handle_go_to_organization,
                    ),
                ),
                Back(Const("◀️ Назад")),
            ),

            state=model.MainMenuStates.personal_cabinet,
            getter=self.personal_profile_service.get_personal_profile_data,
            parse_mode="HTML",
        )