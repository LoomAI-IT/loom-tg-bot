from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.kbd import Button, Row, Back
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class UpdateOrganizationDialog(interface.IUpdateOrganizationDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            update_organization_service: interface.IUpdateOrganizationService,
            update_organization_getter: interface.IUpdateOrganizationGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.update_organization_service = update_organization_service
        self.update_organization_getter = update_organization_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_update_organization_window(),
            self.get_confirm_cancel_window(),
            self.get_organization_result_window(),
        )

    def get_update_organization_window(self) -> Window:
        return Window(
            Multi(
                Format("{message_to_user}"),
            ),

            MessageInput(
                func=self.update_organization_service.handle_user_message,
            ),

            Button(
                Const("❌ Прервать обновление организации"),
                id="show_confirm_cancel",
                on_click=lambda c, b, d: d.switch_to(model.UpdateOrganizationStates.confirm_cancel),
            ),

            state=model.UpdateOrganizationStates.update_organization,
            getter=self.update_organization_getter.get_update_organization_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_confirm_cancel_window(self) -> Window:
        return Window(
            Multi(
                Const("⚠️ <b>Подтверждение завершения</b><br><br>"),
                Const("Вы уверены, что хотите прервать обновление организации?<br><br>"),
                Const("🚨 <b>Внимание:</b> <i>При завершении диалог невозможно будет восстановить!</i><br>"),
                Const("Весь прогресс обновления организации будет потерян."),
                sep="",
            ),

            Row(
                Button(
                    Const("✅ Да, завершить"),
                    id="confirm_cancel",
                    on_click=self.update_organization_service.handle_confirm_cancel,
                ),
                Back(Const("❌ Продолжить диалог")),
            ),

            state=model.UpdateOrganizationStates.confirm_cancel,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_organization_result_window(self) -> Window:
        return Window(
            Const("Ваша организация обновлена"),

            Button(
                Const("🏠 В главное меню"),
                id="go_to_main_menu",
                on_click=self.update_organization_service.handle_go_to_main_menu,
            ),

            state=model.UpdateOrganizationStates.organization_updated,
            parse_mode=SULGUK_PARSE_MODE,
        )
