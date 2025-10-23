from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.kbd import Button
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class CreateCategoryDialog(interface.ICreateCategoryDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            create_category_service: interface.ICreateCategoryService,
            create_category_getter: interface.ICreateCategoryGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.create_category_service = create_category_service
        self.create_category_getter = create_category_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_create_category_window(),
            self.get_category_result_window(),
        )

    def get_create_category_window(self) -> Window:
        return Window(
            Multi(
                Format("{message_to_user}"),
            ),

            MessageInput(
                func=self.create_category_service.handle_user_message,
            ),

            Button(
                Const("❌ Прервать создание рубрики"),
                id="go_to_main_menu",
                on_click=self.create_category_service.handle_go_to_main_menu,
            ),

            state=model.CreateCategoryStates.create_category,
            getter=self.create_category_getter.get_create_category_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_category_result_window(self) -> Window:
        return Window(
            Format("Рубрика успешно создана!"),

            Button(
                Const("🏠 В главное меню"),
                id="go_to_main_menu",
                on_click=self.create_category_service.handle_go_to_main_menu,
            ),

            state=model.CreateCategoryStates.category_created,
            parse_mode=SULGUK_PARSE_MODE,
        )
