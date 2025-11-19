from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Select, Row, Back
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
            self.get_confirm_cancel_window(),
            self.get_category_result_window(),
        )

    def get_select_category_window(self) -> Window:
        return Window(
            Multi(
                Const("🎯 <b>Выберите рубрику для обновления</b><br><br>"),
                Const("💡 <b>Что вас ждет:</b><br>"),
                Const("После выбора рубрики Loom поможет вам улучшить генерацию контента через дружественный диалог.<br><br>"),
                Const("📝 <b>Что можно обновить:</b><br>"),
                Const("• Стиль общения<br>"),
                Const("• Правила бренда и оформления<br>"),
                Const("• Примеры публикаций (хорошие и плохие)<br>"),
                Const("• Стратегию призывов к действию (CTA)<br>"),
                Const("• Длину постов, хештеги и другие параметры<br><br>"),
                Const("🎯 <b>Зачем это нужно:</b><br>"),
                Const("Система анализирует ваши реальные примеры и извлекает паттерны успешного контента. Чем точнее настройки — тем лучше качество генерации.<br><br>"),
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
                Const("🏠 В главное меню"),
                id="cancel_to_main_menu",
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
                Const("❌ Прервать обновление рубрики"),
                id="show_confirm_cancel",
                on_click=lambda c, b, d: d.switch_to(model.UpdateCategoryStates.confirm_cancel),
            ),

            state=model.UpdateCategoryStates.update_category,
            getter=self.update_category_getter.get_update_category_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_confirm_cancel_window(self) -> Window:
        return Window(
            Multi(
                Const("⚠️ <b>Подтверждение завершения</b><br><br>"),
                Const("Вы уверены, что хотите прервать обновление рубрики?<br><br>"),
                Const("🚨 <b>Внимание:</b> <i>При завершении диалог невозможно будет восстановить!</i><br>"),
                Const("Весь прогресс обновления рубрики будет потерян."),
                sep="",
            ),

            Row(
                Button(
                    Const("✅ Да, завершить"),
                    id="confirm_cancel",
                    on_click=self.update_category_service.handle_confirm_cancel,
                ),
                Back(Const("❌ Продолжить диалог")),
            ),

            state=model.UpdateCategoryStates.confirm_cancel,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_category_result_window(self) -> Window:
        return Window(
            Const("Ваша рубрика обновлена"),

            Button(
                Const("🏠 В главное меню"),
                id="go_to_main_menu",
                on_click=self.update_category_service.handle_go_to_main_menu,
            ),

            state=model.UpdateCategoryStates.category_updated,
            parse_mode=SULGUK_PARSE_MODE,
        )