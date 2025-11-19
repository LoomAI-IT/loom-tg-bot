from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Column, Back
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class OrganizationMenuDialog(interface.IOrganizationMenuDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            organization_menu_service: interface.IOrganizationMenuService,
            organization_menu_getter: interface.IOrganizationMenuGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.organization_menu_service = organization_menu_service
        self.organization_menu_getter = organization_menu_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_organization_menu_window(),
        )

    def get_organization_menu_window(self) -> Window:
        return Window(
            Const("🏢 <b>Профиль организации</b> ✨<br><br>"),
            Format("🏷️ Название: <code>{organization_name}</code><br>"),
            Format("💰 Баланс: <code>{balance}</code> руб.<br><br>"),
            Format("📊 <b>Рубрики:</b> 📝<br>"),
            Format("{categories_list}"),

            Column(
                Button(
                    Const("🏢 Обновить параметры организации"),
                    id="update_organization",
                    on_click=self.organization_menu_service.handle_go_to_update_organization,
                ),
                Button(
                    Const("📌 Обновить рубрику"),
                    id="update_category",
                    on_click=self.organization_menu_service.handle_go_to_update_category,
                ),
                Button(
                    Const("⚙️ Настройка сотрудников"),
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
                    Const("🏠 В главное меню"),
                    id="to_main_menu",
                    on_click=self.organization_menu_service.handle_go_to_main_menu,
                ),
            ),

            state=model.OrganizationMenuStates.organization_menu,
            getter=self.organization_menu_getter.get_organization_menu_data,
            parse_mode=SULGUK_PARSE_MODE,
        )