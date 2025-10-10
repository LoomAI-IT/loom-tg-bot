from aiogram import F
from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, ScrollingGroup, Select, NumberedPager, Checkbox
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class PublicationDraftDialog(interface.IPublicationDraftDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            publication_draft_service: interface.IPublicationDraftService,
            publication_draft_getter: interface.IPublicationDraftGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.publication_draft_service = publication_draft_service
        self.publication_draft_getter = publication_draft_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_publication_list_window(),
            self.get_edit_preview_window(),
            self.get_edit_text_menu_window(),
            self.get_edit_text_window(),
            self.get_edit_image_menu_window(),
            self.get_upload_image_window(),
            self.get_social_network_select_window(),
            self.get_publication_success_window(),
        )

    def get_publication_list_window(self) -> Window:
        """
        Список черновиков публикаций.
        Показывает превью текущего черновика с навигацией как в модерации.
        """
        return Window(
            Multi(
                Const("📄 <b>Черновики публикаций</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Format("{publication_text}<br><br>"),
                            Format("👤 <b>Автор:</b> {creator_name}<br>"),
                            Format("🏷️ <b>Рубрика:</b> {category_name}<br>"),
                            Format("📅 <b>Создано:</b> <code>{created_at}</code><br>"),
                        ),
                        False: Multi(
                            Const("✅ <b>Нет черновиков публикаций</b><br><br>"),
                            Const("💫 <i>Создайте первый черновик в генерации публикаций</i>"),
                        ),
                    },
                    selector="has_publications"
                ),
                sep="",
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            Row(
                Button(
                    Const("⬅️ Пред"),
                    id="prev_publication",
                    on_click=self.publication_draft_service.handle_navigate_publication,
                    when="has_prev",
                ),
                Button(
                    Format("📊 {current_index}/{total_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer("📈 Навигация по черновикам"),
                    when="has_publications",
                ),
                Button(
                    Const("➡️ След"),
                    id="next_publication",
                    on_click=self.publication_draft_service.handle_navigate_publication,
                    when="has_next",
                ),
                when="has_publications",
            ),

            Column(
                Row(
                    Button(
                        Const("✏️ Редактировать"),
                        id="edit",
                        on_click=lambda c, b, d: d.switch_to(model.PublicationDraftStates.edit_preview),
                    ),
                    Button(
                        Const("🌐 Выбрать платформы"),
                        id="select_social_network",
                        on_click=self.publication_draft_service.handle_go_to_social_network_select,
                    ),
                ),
                Row(
                    Button(
                        Const("📤 Отправить на модерацию"),
                        id="send_to_moderation",
                        on_click=self.publication_draft_service.handle_send_to_moderation_with_networks_publication,
                    ),
                    Button(
                        Const("🚀 Опубликовать сейчас"),
                        id="publish_now",
                        on_click=self.publication_draft_service.handle_publish_with_selected_networks_publication,
                    ),
                ),
                when="has_publications",
            ),

            Row(
                Button(
                    Const("◀️ Меню контента"),
                    id="back_to_content_menu",
                    on_click=self.publication_draft_service.handle_back_to_content_menu,
                ),
            ),

            state=model.PublicationDraftStates.publication_list,
            getter=self.publication_draft_getter.get_publication_list_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_preview_window(self) -> Window:
        """
        Превью черновика.
        Показывает превью черновика с кнопками редактирования.
        """
        return Window(
            Multi(
                Const("✏️ <b>Редактирование публикации</b><br><br>"),
                Format("{publication_text}<br><br>"),
                Format("👤 <b>Автор:</b> {creator_name}<br>"),
                Format("🏷️ <b>Рубрика:</b> {category_name}<br>"),
                Format("📅 <b>Создано:</b> <code>{created_at}</code><br>"),
                Case(
                    {
                        True: Format("<br>🖼️ <b>Изображение {current_image_index} из {total_images}</b>"),
                        False: Const(""),
                    },
                    selector="has_multiple_images"
                ),
                Case(
                    {
                        True: Const("<br><br>⚠️ <b><i>Есть несохраненные изменения!</i></b>"),
                        False: Const(""),
                    },
                    selector="has_changes"
                ),
                Const("<br><br>📌 <b>Что будем изменять?</b>"),
                sep="",
            ),

            Row(
                Button(
                    Const("⬅️ Пред черновик"),
                    id="prev_publication",
                    on_click=self.publication_draft_service.handle_navigate_publication,
                    when="has_prev",
                ),
                Button(
                    Format("📍 {current_index}/{total_count}"),
                    id="current_position",
                    on_click=None,
                ),
                Button(
                    Const("➡️ След черновик"),
                    id="next_publication",
                    on_click=self.publication_draft_service.handle_navigate_publication,
                    when="has_next",
                ),
                when="has_multiple_drafts",
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            Row(
                Button(
                    Const("⬅️ Пред изображение"),
                    id="prev_image",
                    on_click=self.publication_draft_service.handle_prev_image,
                    when="has_multiple_images",
                ),
                Button(
                    Const("➡️ След изображение"),
                    id="next_image",
                    on_click=self.publication_draft_service.handle_next_image,
                    when="has_multiple_images",
                ),
                when="has_multiple_images",
            ),

            Row(
                Button(
                    Const("✏️ Текст"),
                    id="edit_text",
                    on_click=self.publication_draft_service.handle_back_to_edit_text_menu,
                ),
                Button(
                    Const("🎨 Изображение"),
                    id="edit_image",
                    on_click=self.publication_draft_service.handle_go_to_edit_image_menu,
                ),
            ),

            Row(
                Button(
                    Const("💾 Сохранить изменения"),
                    id="save_changes",
                    on_click=self.publication_draft_service.handle_save_changes,
                    when="has_changes",
                ),
            ),

            Row(
                Button(
                    Const("🗑 Удалить"),
                    id="delete",
                    on_click=self.publication_draft_service.handle_delete_publication,
                ),
            ),

            Row(
                Button(
                    Const("🌐 Выбрать платформы"),
                    id="select_social_network",
                    on_click=self.publication_draft_service.handle_go_to_social_network_select,
                ),
                Button(
                    Const("🚀 Опубликовать сейчас"),
                    id="publish_now",
                    on_click=self.publication_draft_service.handle_publish_with_selected_networks_publication,
                ),
            ),

            Row(
                Button(
                    Const("◀️ Меню контента"),
                    id="back_to_content_menu",
                    on_click=self.publication_draft_service.handle_back_to_content_menu,
                ),
            ),

            state=model.PublicationDraftStates.edit_preview,
            getter=self.publication_draft_getter.get_edit_preview_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_text_menu_window(self) -> Window:
        """Меню редактирования текста."""
        return Window(
            Multi(
                Case(
                    {
                        False: Multi(
                            Const("📝 <b>Редактирование текста</b><br><br>"),
                            Const("🤖 <i>Опишите, что нужно изменить в тексте — я отредактирую его!</i><br><br>"),
                            Const("💡 <b>Примеры:</b><br>"),
                            Const("• «Сделай текст короче и добавь призыв к действию»<br>"),
                            Const("• «Убери сложные термины, пиши проще»<br>"),
                            Const("• «Добавь больше эмоций и хештеги»"),
                        ),
                        True: Case(
                            {
                                True: Multi(
                                    Format("📋 <b>Ваши указания:</b><br>💭 <i>«{regenerate_prompt}»</i><br><br>"),
                                    Const("⏳ <b>Перегенерирую текст...</b><br>"),
                                    Const("🕐 <i>Это может занять время. Пожалуйста, подождите</i>"),
                                ),
                                False: Multi(
                                    Const("⏳ <b>Перегенерирую текст...</b><br>"),
                                    Const("🕐 <i>Это может занять время. Пожалуйста, подождите</i>"),
                                ),
                            },
                            selector="has_regenerate_prompt"
                        )
                    },
                    selector="is_regenerating_text"
                ),
                sep="",
            ),

            Column(
                Button(
                    Const("🔄 Перегенерировать текст"),
                    id="regenerate_all",
                    on_click=self.publication_draft_service.handle_regenerate_text,
                    when=~F["is_regenerating_text"]
                ),
                Button(
                    Const("✍️ Написать свой текст"),
                    id="edit_content",
                    on_click=self.publication_draft_service.handle_go_to_edit_text,
                    when=~F["is_regenerating_text"]
                ),
            ),

            TextInput(
                id="regenerate_prompt_input",
                on_success=self.publication_draft_service.handle_regenerate_text_with_prompt,
            ),

            Button(
                Const("◀️ Назад"),
                id="preview",
                on_click=self.publication_draft_service.handle_back_to_edit_preview_from_text_menu,
                when=~F["is_regenerating_text"]
            ),

            state=model.PublicationDraftStates.edit_text_menu,
            getter=self.publication_draft_getter.get_edit_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_text_window(self) -> Window:
        """Редактирование основного текста."""
        return Window(
            Multi(
                Const("✍️ <b>Редактирование текста</b><br><br>"),
                Const("<b>Ваш текст:</b><br>"),
                Format("{publication_text}<br><br>"),
                Const("📝 <i>Напишите итоговый текст публикации</i>"),
                Case(
                    {
                        True: Const("<br><br>❌ <b>Ошибка:</b> Текст не может быть пустым"),
                        False: Const(""),
                    },
                    selector="has_void_text"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком короткий текст</b><br>💡 <i>Минимум 50 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_small_text"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком длинный текст</b><br>⚠️ <i>Максимум 4000 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_big_text"
                ),
                sep="",
            ),

            TextInput(
                id="text_input",
                on_success=self.publication_draft_service.handle_edit_text,
            ),

            Button(
                Const("◀️ Назад"),
                id="edit_text_menu",
                on_click=self.publication_draft_service.handle_back_to_edit_text_menu,
            ),

            state=model.PublicationDraftStates.edit_text,
            getter=self.publication_draft_getter.get_edit_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_image_menu_window(self) -> Window:
        """Управление изображением."""
        return Window(
            Multi(
                Const("🖼 <b>Управление изображением</b>\n\n"),
                Case(
                    {
                        True: Const("✅ <b>Изображение добавлено</b>\n\n"),
                        False: Const("❌ <b>Изображение отсутствует</b>\n\n"),
                    },
                    selector="has_image"
                ),
                Const("📌 <b>Выберите действие:</b>"),
                sep="",
            ),

            Column(
                Button(
                    Const("📤 Загрузить своё"),
                    id="upload_image",
                    on_click=self.publication_draft_service.handle_go_to_upload_image,
                ),
                Button(
                    Const("🗑 Удалить изображение"),
                    id="remove_image",
                    on_click=self.publication_draft_service.handle_remove_image,
                    when="has_image",
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_preview",
                on_click=self.publication_draft_service.handle_back_to_edit_preview,
            ),

            state=model.PublicationDraftStates.edit_image_menu,
            getter=self.publication_draft_getter.get_image_menu_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_upload_image_window(self) -> Window:
        """Загрузка своего изображения."""
        return Window(
            Multi(
                Const("📤 <b>Загрузка изображения</b>\n\n"),
                Const("📸 <b>Отправьте изображение:</b>\n"),
                Const("<i>Поддерживаются форматы: JPG, PNG, GIF</i>\n"),
                Const("<i>Максимальный размер: 10 МБ</i>"),
                sep="",
            ),

            MessageInput(
                func=self.publication_draft_service.handle_image_upload,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_image_menu",
                on_click=self.publication_draft_service.handle_go_to_edit_image_menu,
            ),

            state=model.PublicationDraftStates.upload_image,
            getter=self.publication_draft_getter.get_upload_image_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_social_network_select_window(self) -> Window:
        """Выбор соцсетей для публикации."""
        return Window(
            Multi(
                Const("🌐 <b>Выбор социальных сетей</b>\n\n"),
                Const("📋 <b>Доступные социальные сети:</b>\n\n"),
                Const("✅ <b>Выберите, где опубликовать:</b>"),
                sep="",
            ),

            Column(
                Checkbox(
                    Const("✅ Telegram"),
                    Const("❌ Telegram"),
                    id="telegram_checkbox",
                    default=False,
                    on_state_changed=self.publication_draft_service.handle_toggle_social_network,
                    when="telegram_connected",
                ),
                Checkbox(
                    Const("✅ VKontakte"),
                    Const("❌ VKontakte"),
                    id="vkontakte_checkbox",
                    default=False,
                    on_state_changed=self.publication_draft_service.handle_toggle_social_network,
                    when="vkontakte_connected",
                ),
            ),

            Row(
                Button(
                    Const("🚀 Опубликовать"),
                    id="publish_with_networks",
                    on_click=self.publication_draft_service.handle_publish_with_selected_networks_publication,
                ),
                Button(
                    Const("◀️ Назад"),
                    id="back_to_preview",
                    on_click=self.publication_draft_service.handle_back_to_edit_preview,
                ),
            ),

            state=model.PublicationDraftStates.social_network_select,
            getter=self.publication_draft_getter.get_social_network_select_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_publication_success_window(self) -> Window:
        """Окно успешной публикации."""
        return Window(
            Multi(
                Const("🎉 <b>Публикация успешно размещена!</b><br>"),
                Case(
                    {
                        True: Multi(
                            Const("🔗 <b>Ссылки на ваши посты:</b><br>"),
                            Case(
                                {
                                    True: Format(
                                        "📱 <b>Telegram:</b> <a href='{telegram_link}'>Перейти к посту</a><br>"),
                                    False: Const(""),
                                },
                                selector="has_telegram_link"
                            ),
                            Case(
                                {
                                    True: Format(
                                        "🔵 <b>ВКонтакте:</b> <a href='{vkontakte_link}'>Перейти к посту</a><br>"),
                                    False: Const(""),
                                },
                                selector="has_vkontakte_link"
                            ),
                            Const("<br>💡 <i>Ссылки сохранены и доступны в разделе \"Мои публикации\"</i>"),
                        ),
                        False: Const("📝 <i>Публикация размещена, но ссылки пока недоступны</i>"),
                    },
                    selector="has_post_links"
                ),
                sep="",
            ),

            Button(
                Const("📋 К списку черновиков"),
                id="go_to_draft_list",
                on_click=self.publication_draft_service.handle_back_to_publication_list,
            ),

            state=model.PublicationDraftStates.publication_success,
            getter=self.publication_draft_getter.get_publication_success_data,
            parse_mode=SULGUK_PARSE_MODE,
        )