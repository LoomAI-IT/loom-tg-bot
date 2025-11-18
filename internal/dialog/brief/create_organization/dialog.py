from aiogram_dialog import Window, Dialog, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Back
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class CreateOrganizationDialog(interface.ICreateOrganizationDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            create_organization_service: interface.ICreateOrganizationService,
            create_organization_getter: interface.ICreateOrganizationGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.create_organization_service = create_organization_service
        self.create_organization_getter = create_organization_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_create_organization_window(),
            self.get_confirm_cancel_window(),
            self.get_organization_result_window(),
        )

    def get_create_organization_window(self) -> Window:
        return Window(
            Multi(
                Format("{message_to_user}"),
            ),

            MessageInput(
                func=self.create_organization_service.handle_user_message,
            ),

            Button(
                Const("❌ Прервать создание организации"),
                id="show_confirm_cancel",
                on_click=lambda c, b, d: d.switch_to(model.CreateOrganizationStates.confirm_cancel),
            ),

            state=model.CreateOrganizationStates.create_organization,
            getter=self.create_organization_getter.get_create_organization_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_confirm_cancel_window(self) -> Window:
        return Window(
            Multi(
                Const("⚠️ <b>Подтверждение завершения</b><br><br>"),
                Const("Вы уверены, что хотите прервать создание организации?<br><br>"),
                Const("🚨 <b>Внимание:</b> <i>При завершении диалог невозможно будет восстановить!</i><br>"),
                Const("Весь прогресс создания организации будет потерян."),
                sep="",
            ),

            Row(
                Button(
                    Const("✅ Да, завершить"),
                    id="confirm_cancel",
                    on_click=self.create_organization_service.handle_confirm_cancel,
                ),
                Back(Const("❌ Продолжить диалог")),
            ),

            state=model.CreateOrganizationStates.confirm_cancel,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_organization_result_window(self) -> Window:
        return Window(
            Const("✅ <b>Отлично! Организация создана.</b><br><br>"),
            Const("🎁 Мы автоматически сгенерировали<br>"),
            Const("2 рубрики для быстрого старта,<br>"),
            Const("чтобы вы могли опробовать инструмент.<br><br>"),
            Const("💡 <b>В будущем вы сможете добавить:</b><br>"),
            Const("• Продукты и услуги компании<br>"),
            Const("• Ограничения для контента<br>"),
            Const("• Дополнительную информацию<br><br>"),
            Const("Для этого перейдите:<br>"),
            Const("<b>Меню организации → Обновить организацию</b>"),

            Button(
                Const("📝 Попробовать сгенерировать публикацию"),
                id="go_to_select_category",
                on_click=self.create_organization_service.go_to_select_category,
            ),

            state=model.CreateOrganizationStates.organization_created,
            parse_mode=SULGUK_PARSE_MODE,
        )
