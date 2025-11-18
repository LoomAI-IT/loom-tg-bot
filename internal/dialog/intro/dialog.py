from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Url, Back
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class IntroDialog(interface.IIntroDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            intro_service: interface.IIntroService,
            intro_getter: interface.IIntroGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.intro_service = intro_service
        self.intro_getter = intro_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_welcome_window(),
            self.get_user_agreement_window(),
            self.get_privacy_policy_window(),
            self.get_data_processing_window(),
            self.get_intro_window(),
            self.get_join_to_organization_window(),
        )

    def get_welcome_window(self) -> Window:
        return Window(
            Const("👋 <b>Добро пожаловать в Loom</b><br><br>"),
            Const("AI SMM инструмент<br>"),
            Const("для снижения затрат на рутину.<br><br>"),
            Const("<b>Как это работает:</b><br><br>"),
            Const("Сотрудник говорит голосом 🎤<br>"),
            Const("<blockquote>\"У нас крутой кейс с клиентом,<br>"),
            Const("проект сделали за неделю!\"</blockquote><br><br>"),
            Const("Через пару минут получаете:<br>"),
            Const("✍️ Текст в стиле бренда<br>"),
            Const("🎨 Картинку под рубрику<br>"),
            Const("📱 Пост для всех соцсетей<br><br>"),
            Const("<b>Вместо:</b> ⏱ 2-3 часа работы SMM<br>"),
            Const("<b>Получаете:</b> ⚡️ 5 минут на команду<br><br>"),
            Const("Больше контента.<br>"),
            Const("Меньше времени.<br>"),
            Const("Меньше бюджета. 💰"),
            Button(
                Const("Продолжить ➡️"),
                id="continue_to_agreements",
                on_click=lambda c, b, d: d.switch_to(model.IntroStates.user_agreement, ShowMode.EDIT),
            ),
            state=model.IntroStates.welcome,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_user_agreement_window(self) -> Window:
        return Window(
            Const("📋 <b>1/3 Перед началом работы необходимо принять пользовательское соглашение:</b><br>"),
            Url(
                Const("📖 Читать соглашение"),
                Format("{user_agreement_link}"),
            ),
            Button(
                Const("✅ Принять"),
                id="accept_user_agreement",
                on_click=self.intro_service.accept_user_agreement,
            ),
            state=model.IntroStates.user_agreement,
            getter=self.intro_getter.get_agreement_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_privacy_policy_window(self) -> Window:
        return Window(
            Const("🔒 <b>2/3 Перед началом работы необходимо принять политику конфиденциальности:</b><br>"),
            Url(
                Const("📖 Читать политику"),
                Format("{privacy_policy_link}"),
            ),
            Button(
                Const("✅ Принять"),
                id="accept_privacy_policy",
                on_click=self.intro_service.accept_privacy_policy,
            ),
            Back(Const("◀️ Назад")),
            state=model.IntroStates.privacy_policy,
            getter=self.intro_getter.get_agreement_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_data_processing_window(self) -> Window:
        return Window(
            Const("📊 <b>3/3 Перед началом работы необходимо принять согласие на обработку персональных данных:</b><br>"),
            Url(
                Const("📖 Читать согласие"),
                Format("{data_processing_link}"),
            ),
            Button(
                Const("✅ Принять"),
                id="accept_data_processing",
                on_click=self.intro_service.accept_data_processing,
            ),
            Back(Const("◀️ Назад")),
            state=model.IntroStates.data_processing,
            getter=self.intro_getter.get_agreement_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_intro_window(self) -> Window:
        return Window(
            Const("Перед переходом к работе с контентом, выбери"),
            Button(
                Const("Вступить в организацию"),
                id="join_to_organization",
                on_click=lambda c, b, d: d.switch_to(model.IntroStates.join_to_organization, ShowMode.EDIT),
            ),
            Button(
                Const("Создать организацию"),
                id="create_organization",
                on_click=self.intro_service.go_to_create_organization
            ),
            state=model.IntroStates.intro,
            getter=self.intro_getter.get_agreement_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_join_to_organization_window(self) -> Window:
        return Window(
            Format("Ваш ID: <code>{account_id}</code><br><br>"),
            Const("Отправьте его тому, кто пригласил вас в Loom"),
            Button(
                Const("Назад"),
                id="contact_support",
                on_click=lambda c, b, d: d.switch_to(model.IntroStates.intro, ShowMode.EDIT),
            ),
            state=model.IntroStates.join_to_organization,
            getter=self.intro_getter.get_user_status,
            parse_mode=SULGUK_PARSE_MODE,
        )