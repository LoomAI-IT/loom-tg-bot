from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Select
from aiogram_dialog.widgets.input import MessageInput
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class UpdateCategoryDialog(interface.IUpdateCategoryDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            update_category_service: interface.IUpdateCategoryService,
            update_category_getter: interface.IUpdateCategoryGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.update_category_service = update_category_service
        self.update_category_getter = update_category_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_select_category_window(),
            self.get_update_category_window(),
            self.get_category_result_window(),
        )

    def get_select_category_window(self) -> Window:
        return Window(
            Multi(
                Const("🎯 <b>Выберите рубрику для обновления</b><br>"),
                Case(
                    {
                        True: Const("📋 <b>Доступные рубрики:</b>"),
                        False: Multi(
                            Const("🚫 <b>Рубрики не созданы</b><br>"),
                            Const("💡 <i>Создайте первую рубрику</i>"),
                        ),
                    },
                    selector="has_categories"
                ),
                sep="",
            ),

            Column(
                Select(
                    Format("📌 {item[name]}"),
                    id="category_select",
                    items="categories",
                    item_id_getter=lambda item: str(item["id"]),
                    on_click=self.update_category_service.handle_select_category,
                    when="has_categories",
                ),
            ),

            Button(
                Const("В главное меню"),
                id="cancel_to_content_menu",
                on_click=self.update_category_service.handle_go_to_main_menu,
            ),

            state=model.UpdateCategoryStates.select_category,
            getter=self.update_category_getter.get_select_category_data,
            parse_mode=SULGUK_PARSE_MODE,
        )
    
    def get_update_category_window(self) -> Window:
        return Window(
            Multi(
                Format("{message_to_user}"),
            ),

            MessageInput(
                func=self.update_category_service.handle_user_message,
            ),

            Button(
                Const("В главное меню"),
                id="go_to_main_menu",
                on_click=self.update_category_service.handle_go_to_main_menu,
            ),

            state=model.UpdateCategoryStates.update_category,
            getter=self.update_category_getter.get_update_category_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_category_result_window(self) -> Window:
        return Window(
            Const("Ваша рубрика обновлена"),

            Button(
                Const("В главное меню"),
                id="go_to_main_menu",
                on_click=self.update_category_service.handle_go_to_main_menu,
            ),

            state=model.UpdateCategoryStates.category_updated,
            parse_mode=SULGUK_PARSE_MODE,
        )