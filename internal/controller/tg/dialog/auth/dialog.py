from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Url, Back
from aiogram.fsm.state import StatesGroup

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class AuthDialog(interface.IAuthDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            auth_dialog_controller: interface.IAuthDialogController,
            auth_dialog_service: interface.IAuthDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.auth_dialog_controller = auth_dialog_controller
        self.auth_dialog_service = auth_dialog_service
        self._dialog = None

    def get_dialog(self) -> Dialog:
        """Возвращает сконфигурированный диалог авторизации"""
        with self.tracer.start_as_current_span(
                "AuthDialog.get_dialog",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                if self._dialog is None:
                    self._dialog = Dialog(
                        self.get_user_agreement_window(),
                        self.get_privacy_policy_window(),
                        self.get_data_processing_window(),
                        self.get_welcome_window(),
                        self.get_access_denied_window(),
                    )

                span.set_status(Status(StatusCode.OK))
                return self._dialog
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    def get_states(self) -> type[StatesGroup]:
        return model.AuthStates

    def get_user_agreement_window(self) -> Window:
        """Окно пользовательского соглашения (1/3)"""
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
                on_click=self.auth_dialog_controller.accept_user_agreement,
            ),
            state=model.AuthStates.user_agreement,
            getter=self.auth_dialog_service.get_agreement_data,
            parse_mode="HTML",
        )

    def get_privacy_policy_window(self) -> Window:
        """Окно политики конфиденциальности (2/3)"""
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
                on_click=self.auth_dialog_controller.accept_privacy_policy,
            ),
            Back(Const("◀️ Назад")),
            state=model.AuthStates.privacy_policy,
            getter=self.auth_dialog_service.get_agreement_data,
            parse_mode="HTML",
        )

    def get_data_processing_window(self) -> Window:
        """Окно согласия на обработку данных (3/3)"""
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
                on_click=self.auth_dialog_controller.accept_data_processing,
            ),
            Back(Const("◀️ Назад")),
            state=model.AuthStates.data_processing,
            getter=self.auth_dialog_service.get_agreement_data,
            parse_mode="HTML",
        )

    def get_welcome_window(self) -> Window:
        """Приветственное окно после успешной авторизации"""
        return Window(
            Format("👋 <b>Привет, {name}! Я — твой контент-бот.</b>\n\n"),
            Const(
                "🤖 Я помогу тебе быстро создать и опубликовать пост с помощью "
                "искусственного интеллекта. Просто отправь текст или голосовое "
                "сообщение — и начнём магию!\n\n"
                "🎬 Для создания коротких видео отправь ссылку на YouTube-видео\n\n"
                "✨ Готов? Тогда жду твоего сообщения!"
            ),
            Button(
                Const("🚀 Начать работу"),
                id="go_to_main_menu",
                on_click=None,
            ),
            state=model.AuthStates.welcome,
            getter=self.auth_dialog_service.get_user_status,
            parse_mode="HTML",
        )

    def get_access_denied_window(self) -> Window:
        """Окно отказа в доступе"""
        return Window(
            Const("🚫 <b>Доступ ограничен</b>\n\n"),
            Const(
                "Извините, но у вашего аккаунта недостаточно прав для "
                "использования этого бота.\n\n"
                "<b>Что можно сделать:</b>\n"
                "• Обратитесь к своему администратору\n"
                "• Напишите в поддержку"
            ),
            Button(
                Const("📞 Поддержка"),
                id="contact_support",
                on_click=self.auth_dialog_controller.handle_access_denied,
            ),
            state=model.AuthStates.access_denied,
            getter=self.auth_dialog_service.get_user_status,
            parse_mode="HTML",
        )