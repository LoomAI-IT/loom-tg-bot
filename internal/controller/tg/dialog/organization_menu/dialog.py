from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Column, Back

from internal import interface, model


class OrganizationMenuDialog(interface.IOrganizationMenuDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            organization_menu_service: interface.IOrganizationMenuDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.organization_menu_service = organization_menu_service

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_organization_menu_window(),
        )

    def get_organization_menu_window(self) -> Window:
        return Window(
            Const("🏢 <b>Профиль организации</b>\n\n"),
            Format("• Название: <b>{organization_name}</b>\n"),
            Format("• Баланс: <b>{balance}</b> руб.\n"),
            Format("📍 <b>Доступные платформы для публикаций:</b>\n"),
            Format("{platforms_list}\n\n"),
            Format("📊 <b>Рубрики:</b>\n"),
            Format("{categories_list}"),

            Column(
                Button(
                    Const("⚙️ Настройка пользователей"),
                    id="user_settings",
                    on_click=self.organization_menu_service.handle_go_to_employee_settings,
                ),
                Button(
                    Const("👥 Добавить сотрудника"),
                    id="add_employee",
                    on_click=self.organization_menu_service.handle_go_to_add_employee,
                ),
                Button(
                    Const("💰 Пополнить баланс"),
                    id="top_up_balance",
                    on_click=self.organization_menu_service.handle_go_to_top_up_balance,
                ),
                Button(
                    Const("🌐 Социальные сети"),
                    id="social_networks",
                    on_click=self.organization_menu_service.handle_go_to_social_networks,
                ),
                Button(
                    Const("В главное меню"),
                    id="to_main_menu",
                    on_click=self.organization_menu_service.handle_go_to_main_menu,
                ),
            ),

            state=model.OrganizationMenuStates.organization_menu,
            getter=self.organization_menu_service.get_organization_menu_data,
            parse_mode="HTML",
        )
