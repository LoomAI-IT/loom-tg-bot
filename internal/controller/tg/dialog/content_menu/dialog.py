from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back

from internal import interface, model


class ContentMenuDialog(interface.IContentMenuDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            content_menu_service: interface.IContentMenuDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.content_menu_service = content_menu_service

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_content_menu_window(),
            self.get_content_type_selection_window(),
            self.get_drafts_type_selection_window(),
            self.get_moderation_type_selection_window(),
        )

    def get_content_menu_window(self) -> Window:
        return Window(
            Const("✍️ <b>Контент и публикации</b>\n\n"),
            Const("🎯 <b>Что хотите сделать?</b>\n\n"),
            Format("📊 <b>Статистика:</b>\n"),
            Format("• Черновиков: <b>{drafts_count}</b>\n"),
            Format("• На модерации: <b>{moderation_count}</b>\n"),
            Format("• Прошли модерацию: <b>{approved_count}</b>\n"),
            Format("• Опубликовано: <b>{published_count}</b>\n"),
            Format("• Сгенерированно публикаций: <b>{publication_count}</b>\n"),
            Format("• Сгенерировано нарезок: <b>{video_cut_count}</b>\n"),
            Format("• Всего генераций: <b>{total_generations}</b>\n\n"),

            Column(
                Button(
                    Const("🚀 Создать новый контент"),
                    id="create_content",
                    on_click=lambda c, b, d: d.switch_to(model.ContentMenuStates.select_content_type),
                ),
                Row(
                    Button(
                        Const("📝 Черновики"),
                        id="drafts",
                        on_click=lambda c, b, d: d.switch_to(model.ContentMenuStates.select_drafts_type),
                    ),
                    Button(
                        Const("🔍 Модерация"),
                        id="moderation",
                        on_click=lambda c, b, d: d.switch_to(model.ContentMenuStates.select_moderation_type),
                    ),
                ),
                Button(
                    Const("🏠 В главное меню"),
                    id="to_main_menu",
                    on_click=self.content_menu_service.handle_go_to_main_menu,
                ),
            ),

            state=model.ContentMenuStates.content_menu,
            getter=self.content_menu_service.get_content_menu_data,
            parse_mode="HTML",
        )

    def get_content_type_selection_window(self) -> Window:
        return Window(
            Const("🎯 <b>Выберите тип контента для создания</b>\n\n"),

            Column(
                Button(
                    Const("📝 Публикация с текстом и изображением"),
                    id="create_publication",
                    on_click=self.content_menu_service.handle_go_to_publication_generation,
                ),
                Button(
                    Const("🎬 Короткие видео из YouTube"),
                    id="create_video_cut",
                    on_click=self.content_menu_service.handle_go_to_video_cut_generation,
                ),
            ),

            Button(
                Const("🏠 Обратно в меню контента"),
                id="to_content_menu",
                on_click=self.content_menu_service.handle_go_to_content_menu,
            ),

            state=model.ContentMenuStates.select_content_type,
            parse_mode="HTML",
        )

    def get_drafts_type_selection_window(self) -> Window:
        return Window(
            Const("📝 <b>Выберите тип черновиков</b>\n\n"),
            Format("📊 <b>Статистика черновиков:</b>\n"),
            Format("• Публикации: <b>{publication_drafts_count}</b>\n"),
            Format("• Видео-нарезки: <b>{video_drafts_count}</b>\n\n"),

            Column(
                Button(
                    Const("📝 Черновики публикаций"),
                    id="publication_drafts",
                    on_click=self.content_menu_service.handle_go_to_publication_drafts,
                ),
                Button(
                    Const("🎬 Черновики видео-нарезок"),
                    id="video_drafts",
                    on_click=self.content_menu_service.handle_go_to_video_drafts,
                ),
            ),

            Button(
                Const("🏠 Обратно в меню контента"),
                id="to_content_menu",
                on_click=self.content_menu_service.handle_go_to_content_menu,
            ),

            state=model.ContentMenuStates.select_drafts_type,
            getter=self.content_menu_service.get_drafts_type_data,
            parse_mode="HTML",
        )

    def get_moderation_type_selection_window(self) -> Window:
        return Window(
            Const("🔍 <b>Выберите тип модерации</b>\n\n"),
            Format("📊 <b>Статистика модерации:</b>\n"),
            Format("• Публикации на модерации: <b>{publication_moderation_count}</b>\n"),
            Format("• Видео на модерации: <b>{video_moderation_count}</b>\n\n"),

            Column(
                Button(
                    Const("📝 Модерация публикаций"),
                    id="publication_moderation",
                    on_click=self.content_menu_service.handle_go_to_publication_moderation,
                ),
                Button(
                    Const("🎬 Модерация видео-нарезок"),
                    id="video_moderation",
                    on_click=self.content_menu_service.handle_go_to_video_moderation,
                ),
            ),

            Button(
                Const("🏠 Обратно в меню контента"),
                id="to_content_menu",
                on_click=self.content_menu_service.handle_go_to_content_menu,
            ),

            state=model.ContentMenuStates.select_moderation_type,
            getter=self.content_menu_service.get_moderation_type_data,
            parse_mode="HTML",
        )