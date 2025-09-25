from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Case, Multi
from aiogram_dialog.widgets.kbd import Button, Column, Row

from internal import interface, model


class PersonalProfileDialog(interface.IPersonalProfileDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            personal_profile_service: interface.IPersonalProfileService,
            personal_profile_getter: interface.IPersonalProfileGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.personal_profile_service = personal_profile_service
        self.personal_profile_getter = personal_profile_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_personal_profile_window(),
            self.get_faq_window(),
            self.get_support_window()
        )

    def get_personal_profile_window(self) -> Window:
        return Window(
            Format("👤 <b>Личный профиль</b>\n\n"),
            Format("🏢 <b>Организация:</b> {organization_name}\n"),
            Format("👨‍💼 <b>Имя:</b> {employee_name}\n"),
            Format("📱 <b>Телеграм:</b> @{employee_tg_username}\n"),
            Format("🆔 <b>ID аккаунта:</b> <code>{account_id}</code>\n"),
            Format("🎭 <b>Роль:</b> {role_display}\n"),
            Format("📅 <b>В команде с:</b> {created_at}\n\n"),

            Const("📊 <b>Статистика активности</b>\n"),
            Format("✏️ <b>Создано публикаций:</b> {generated_publication_count}\n"),
            Format("🚀 <b>Опубликовано:</b> {published_publication_count}\n"),
            Case(
                {
                    True: Multi(
                        Format("❌ <b>Отклонено модерацией:</b> {rejected_publication_count}\n"),
                        Format("✅ <b>Одобрено модерацией:</b> {approved_publication_count}\n"),
                    ),
                    False: Const("")
                },
                selector="has_moderated_publications"
            ),
            Const("🔐 <b>Права доступа</b>\n"),
            Format("{permissions_text}\n"),

            Column(
                Row(
                    Button(
                        Const("❓ F.A.Q"),
                        id="faq",
                        on_click=self.personal_profile_service.handle_go_faq,
                    ),
                    Button(
                        Const("🆘 Поддержка"),
                        id="support",
                        on_click=self.personal_profile_service.handle_go_to_support,
                    ),
                ),
                Button(
                    Const("🏠 Главное меню"),
                    id="to_main_menu",
                    on_click=self.personal_profile_service.handle_go_to_main_menu,
                ),
            ),

            state=model.PersonalProfileStates.personal_profile,
            getter=self.personal_profile_getter.get_personal_profile_data,
            parse_mode="HTML",
        )

    def get_faq_window(self) -> Window:
        return Window(
            Format("❓ <b>Часто задаваемые вопросы</b>\n\n"),
            Format("📋 <i>Здесь будут размещены ответы на популярные вопросы</i>\n\n"),
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
            Format("🆘 <b>Техническая поддержка</b>\n\n"),
            Format("📞 <i>Контактная информация службы поддержки будет размещена здесь</i>\n\n"),
            Button(
                Const("◀️ Назад"),
                id="back_to_profile",
                on_click=self.personal_profile_service.handle_back_to_profile,
            ),
            state=model.PersonalProfileStates.support,
            parse_mode="HTML",
        )