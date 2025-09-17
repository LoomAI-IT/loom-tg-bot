from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Column, Row

from internal import interface, model


class PersonalProfileDialog(interface.IPersonalProfileDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            personal_profile_service: interface.IPersonalProfileDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.personal_profile_service = personal_profile_service

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_personal_profile_window(),
            self.get_faq_window(),
            self.get_support_window()
        )

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
                        on_click=self.personal_profile_service.handle_go_faq,
                    ),
                    Button(
                        Const("📰 Поддержка"),
                        id="support",
                        on_click=self.personal_profile_service.handle_go_to_support,
                    ),
                ),
                Button(
                    Const("В главное меню"),
                    id="to_main_menu",
                    on_click=self.personal_profile_service.handle_go_to_main_menu,
                ),
            ),

            state=model.PersonalProfileStates.personal_profile,
            getter=self.personal_profile_service.get_personal_profile_data,
            parse_mode="HTML",
        )

    def get_faq_window(self) -> Window:
        return Window(
            Format("<b>Вопросики всякие тут будут</b>\n\n"),
            Button(
                Const("◀️ Назад"),
                id="back_to_profile",
                on_click=self.personal_profile_service.handle_back_to_profile,
            ),
            state=model.PersonalProfileStates.faq,
            parse_mode="HTML",
        )

    def get_support_window(self) -> Window:
        return Window(
            Format("<b>А тут будут контактные данные поддержки</b>\n\n"),
            Button(
                Const("◀️ Назад"),
                id="back_to_profile",
                on_click=self.personal_profile_service.handle_back_to_profile,
            ),
            state=model.PersonalProfileStates.support,
            parse_mode="HTML",
        )