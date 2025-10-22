from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Column, Row
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class ContentMenuDialog(interface.IContentMenuDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            content_menu_service: interface.IContentMenuService,
            content_menu_getter: interface.IContentMenuGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.content_menu_service = content_menu_service
        self.content_menu_getter = content_menu_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_content_menu_window(),
            self.get_content_type_selection_window(),
            self.get_drafts_type_selection_window(),
            self.get_moderation_type_selection_window(),
        )

    def get_content_menu_window(self) -> Window:
        return Window(
            Const("✍️ <b>Контент-студия</b><br><br>"
                  "💡 Создавайте новый контент или работайте с черновиками<br><br>"),

            Format("📊 <b>Ваша статистика:</b><br>"),
            Format("📝 Черновиков: <b>{drafts_count}</b><br>"),
            Format("⏳ На модерации: <b>{moderation_count}</b><br>"),
            Format("✅ Опубликовано: <b>{approved_count}</b><br>"),

            Column(
                Button(
                    Const("🚀 Генерация контента"),
                    id="create_content",
                    on_click=lambda c, b, d: d.switch_to(model.ContentMenuStates.select_content_type),
                ),
                Row(
                    Button(
                        Const("📝 Мои черновики"),
                        id="drafts",
                        on_click=lambda c, b, d: d.switch_to(model.ContentMenuStates.select_drafts_type),
                    ),
                    Button(
                        Const("⏳ На модерации"),
                        id="moderation",
                        on_click=lambda c, b, d: d.switch_to(model.ContentMenuStates.select_moderation_type),
                    ),
                ),
                Button(
                    Const("Создать рубрику"),
                    id="go_to_main_menu",
                    on_click=self.content_menu_service.go_to_create_category,
                    when=~F["has_categories"],
                ),
                Button(
                    Const("🏠 В главное меню"),
                    id="to_main_menu",
                    on_click=self.content_menu_service.handle_go_to_main_menu,
                ),
            ),

            state=model.ContentMenuStates.content_menu,
            getter=self.content_menu_getter.get_content_menu_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_content_type_selection_window(self) -> Window:
        return Window(
            Const("🎯 <b>Что будем создавать?</b><br><br>"
                  "Выберите тип контента для генерации:<br>"),

            Column(
                Button(
                    Const("📰 Публикации"),
                    id="create_publication",
                    on_click=self.content_menu_service.handle_go_to_publication_generation,
                ),
                Button(
                    Const("🎬 Короткие видео"),
                    id="create_video_cut",
                    on_click=self.content_menu_service.handle_go_to_video_cut_generation,
                ),
            ),

            Button(
                Const("⬅️ Назад"),
                id="to_content_menu",
                on_click=self.content_menu_service.handle_go_to_content_menu,
            ),

            state=model.ContentMenuStates.select_content_type,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_drafts_type_selection_window(self) -> Window:
        return Window(
            Const("📝 <b>Ваши черновики</b><br><br>"
                  "Выберите тип черновиков для просмотра:<br><br>"),

            Format("📊 <b>Статистика черновиков:</b><br>"),
            Format("📰 Публикации: <b>{publication_drafts_count}</b><br>"),
            Format("🎬 Видео-нарезки: <b>{video_drafts_count}</b><br>"),

            Column(
                Button(
                    Const("📰 Публикации"),
                    id="publication_drafts",
                    on_click=self.content_menu_service.handle_go_to_publication_drafts,
                ),
                Button(
                    Const("🎬 Видео"),
                    id="video_drafts",
                    on_click=self.content_menu_service.handle_go_to_video_drafts,
                ),
            ),

            Button(
                Const("⬅️ Назад"),
                id="to_content_menu",
                on_click=self.content_menu_service.handle_go_to_content_menu,
            ),

            state=model.ContentMenuStates.select_drafts_type,
            getter=self.content_menu_getter.get_drafts_type_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_moderation_type_selection_window(self) -> Window:
        return Window(
            Const("👀 <b>Модерация контента</b><br><br>"
                  "Выберите тип контента для модерации:<br><br>"),

            Format("📊 <b>Статистика модерации:</b><br>"),
            Format("📰 Публикации на модерации: <b>{publication_moderation_count}</b><br>"),
            Format("🎬 Видео на модерации: <b>{video_moderation_count}</b><br>"),

            Column(
                Button(
                    Const("📰 Публикации"),
                    id="publication_moderation",
                    on_click=self.content_menu_service.handle_go_to_publication_moderation,
                ),
                Button(
                    Const("🎬 Видео"),
                    id="video_moderation",
                    on_click=self.content_menu_service.handle_go_to_video_moderation,
                ),
            ),

            Button(
                Const("⬅️ Назад"),
                id="to_content_menu",
                on_click=self.content_menu_service.handle_go_to_content_menu,
            ),

            state=model.ContentMenuStates.select_moderation_type,
            getter=self.content_menu_getter.get_moderation_type_data,
            parse_mode=SULGUK_PARSE_MODE,
        )