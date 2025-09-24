from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Url, Back

from internal import interface, model


class AuthDialog(interface.IAuthDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            auth_service: interface.IAuthService,
            auth_getter: interface.IAuthGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.auth_service = auth_service
        self.auth_getter = auth_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_user_agreement_window(),
            self.get_privacy_policy_window(),
            self.get_data_processing_window(),
            self.get_access_denied_window(),
        )

    def get_user_agreement_window(self) -> Window:
        return Window(
            Const("📋 <b>1/3 Перед началом работы необходимо принять пользовательское соглашение:</b>\n"),
            Format("{user_agreement_link}"),
            Url(
                Const("📖 Читать соглашение"),
                Format("{user_agreement_link}"),
            ),
            Button(
                Const("✅ Принять"),
                id="accept_user_agreement",
                on_click=self.auth_service.accept_user_agreement,
            ),
            state=model.AuthStates.user_agreement,
            getter=self.auth_getter.get_agreement_data,
            parse_mode="HTML",
        )

    def get_privacy_policy_window(self) -> Window:
        return Window(
            Const("🔒 <b>2/3 Перед началом работы необходимо принять политику конфиденциальности:</b>\n"),
            Format("{privacy_policy_link}"),
            Url(
                Const("📖 Читать политику"),
                Format("{privacy_policy_link}"),
            ),
            Button(
                Const("✅ Принять"),
                id="accept_privacy_policy",
                on_click=self.auth_service.accept_privacy_policy,
            ),
            Back(Const("◀️ Назад")),
            state=model.AuthStates.privacy_policy,
            getter=self.auth_getter.get_agreement_data,
            parse_mode="HTML",
        )

    def get_data_processing_window(self) -> Window:
        return Window(
            Const("📊 <b>3/3 Перед началом работы необходимо принять согласие на обработку персональных данных:</b>\n"),
            Format("{data_processing_link}"),
            Url(
                Const("📖 Читать согласие"),
                Format("{data_processing_link}"),
            ),
            Button(
                Const("✅ Принять"),
                id="accept_data_processing",
                on_click=self.auth_service.accept_data_processing,
            ),
            Back(Const("◀️ Назад")),
            state=model.AuthStates.data_processing,
            getter=self.auth_getter.get_agreement_data,
            parse_mode="HTML",
        )

    def get_access_denied_window(self) -> Window:
        return Window(
            Const("🚫 <b>Доступ ограничен</b>\n\n"),
            Const(
                "Извините, но у вашего аккаунта недостаточно прав для "
                "использования этого бота.\n\n"
                "<b>Что можно сделать:</b>\n"
            ),
            Format("• Обратитесь к своему администратору и сообщите ему ваш ID аккаунта: {account_id}\n"),
            Button(
                Const("📞 Поддержка"),
                id="contact_support",
                on_click=self.auth_service.handle_access_denied,
            ),
            state=model.AuthStates.access_denied,
            getter=self.auth_getter.get_user_status,
            parse_mode="HTML",
        )
