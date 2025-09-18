from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, Select
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia

from internal import interface, model


class ModerationPublicationDialog(interface.IModerationPublicationDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            moderation_publication_service: interface.IModerationPublicationDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.moderation_publication_service = moderation_publication_service

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_moderation_list_window(),
            self.get_reject_comment_window(),
            self.get_edit_preview_window(),
            self.get_edit_title_window(),
            self.get_edit_tags_window(),
            self.get_edit_content_window(),
            self.get_edit_image_menu_window(),
            self.get_generate_image_window(),
            self.get_upload_image_window(),
        )

    def get_moderation_list_window(self) -> Window:
        """Окно списка публикаций на модерации - теперь сразу показывает первую публикацию"""
        return Window(
            Multi(
                Const("🔍 <b>Модерация публикаций</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Format("📊 Всего на модерации: <b>{publications_count}</b>\n"),
                            Format("📅 Период: <b>{period_text}</b>\n\n"),
                            # Показываем информацию о текущей публикации
                            Format("👤 Автор: <b>{author_name}</b>\n"),
                            Format("🏷 Рубрика: <b>{category_name}</b>\n"),
                            Format("📅 Создано: {created_at}\n"),
                            Case(
                                {
                                    True: Format("⏰ Ожидает модерации: <b>{waiting_time}</b>\n"),
                                    False: Const(""),
                                },
                                selector="has_waiting_time"
                            ),
                            Const("━━━━━━━━━━━━━━━━━━━━\n"),
                            Format("<b>{publication_name}</b>\n\n"),
                            Format("{publication_text}\n\n"),
                            Case(
                                {
                                    True: Format("🏷 Теги: {publication_tags}"),
                                    False: Const(""),
                                },
                                selector="has_tags"
                            ),
                            Const("\n━━━━━━━━━━━━━━━━━━━━"),
                        ),
                        False: Multi(
                            Const("✅ <b>Нет публикаций на модерации</b>\n\n"),
                            Const("<i>Все публикации обработаны или еще не поступали</i>"),
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

            # Навигация со счетчиком в одной строке
            Row(
                Button(
                    Const("⬅️"),
                    id="prev_publication",
                    on_click=self.moderation_publication_service.handle_navigate_publication,
                    when="has_prev",
                ),
                Button(
                    Format("{current_index}/{total_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer(),  # Просто показываем позицию
                    when="has_publications",
                ),
                Button(
                    Const("➡️"),
                    id="next_publication",
                    on_click=self.moderation_publication_service.handle_navigate_publication,
                    when="has_next",
                ),
                when="has_publications",
            ),

            # Основные действия
            Column(
                Row(
                    Button(
                        Const("✏️ Редактировать"),
                        id="edit",
                        on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview),
                        when="has_publications",
                    ),
                    Button(
                        Const("✅ Принять"),
                        id="approve",
                        on_click=self.moderation_publication_service.handle_approve_publication,
                        when="has_publications",
                    ),
                ),
                Row(
                    Button(
                        Const("💬 Отклонить"),
                        id="reject_with_comment",
                        on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.reject_comment),
                        when="has_publications",
                    ),
                ),
                when="has_publications",
            ),

            Row(
                Button(
                    Const("◀️ В меню контента"),
                    id="back_to_content_menu",
                    on_click=self.moderation_publication_service.handle_back_to_content_menu,
                ),
            ),

            state=model.ModerationPublicationStates.moderation_list,
            getter=self.moderation_publication_service.get_moderation_list_data,
            parse_mode="HTML",
        )

    def get_reject_comment_window(self) -> Window:
        """Окно ввода комментария при отклонении"""
        return Window(
            Multi(
                Const("❌ <b>Отклонение публикации</b>\n\n"),
                Format("📄 Публикация: <b>{publication_name}</b>\n"),
                Format("👤 Автор: <b>{author_name}</b>\n\n"),
                Const("💬 <b>Укажите причину отклонения:</b>\n"),
                Const("<i>Автор получит уведомление с вашим комментарием</i>\n\n"),
                Case(
                    {
                        True: Multi(
                            Const("📝 <b>Ваш комментарий:</b>\n"),
                            Format("<i>{reject_comment}</i>"),
                        ),
                        False: Const("💭 Ожидание ввода комментария..."),
                    },
                    selector="has_comment"
                ),
                sep="",
            ),

            TextInput(
                id="reject_comment_input",
                on_success=self.moderation_publication_service.handle_reject_comment_input,
            ),

            Row(
                Button(
                    Const("📤 Отправить отклонение"),
                    id="send_rejection",
                    on_click=self.moderation_publication_service.handle_send_rejection,
                    when="has_comment",
                ),
                Button(
                    Const("Назад"),
                    id="back_to_moderation_list",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.moderation_list),
                ),
            ),

            state=model.ModerationPublicationStates.reject_comment,
            getter=self.moderation_publication_service.get_reject_comment_data,
            parse_mode="HTML",
        )

    def get_edit_preview_window(self) -> Window:
        """Окно редактирования с превью публикации"""
        return Window(
            Multi(
                Const("✏️ <b>Редактирование публикации</b>\n\n"),
                # Показываем саму публикацию
                Format("👤 Автор: <b>{author_name}</b>\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n"),
                Format("📅 Создано: {created_at}\n\n"),
                Const("━━━━━━━━━━━━━━━━━━━━\n"),
                Format("<b>{publication_name}</b>\n\n"),
                Format("{publication_text}\n\n"),
                Case(
                    {
                        True: Format("🏷 Теги: {publication_tags}"),
                        False: Const("🏷 Теги: <i>отсутствуют</i>"),
                    },
                    selector="has_tags"
                ),
                Case(
                    {
                        True: Const("\n\n<i>❗️ Есть несохраненные изменения</i>"),
                        False: Const(""),
                    },
                    selector="has_changes"
                ),
                Const("\n━━━━━━━━━━━━━━━━━━━━\n\n"),
                Const("📌 <b>Выберите, что изменить:</b>"),
                sep="",
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            Column(
                Button(
                    Const("✏️ Текст"),
                    id="edit_text_menu",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_text_menu),
                ),
                Button(
                    Const("🖼 Управление изображением"),
                    id="edit_image",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_image_menu),
                ),
            ),

            Row(
                Button(
                    Const("💾 Сохранить изменения"),
                    id="save_edits",
                    on_click=self.moderation_publication_service.handle_save_edits,
                    when="has_changes",
                ),
                Button(
                    Const("Назад"),
                    id="back_to_moderation_list",
                    on_click=self.moderation_publication_service.handle_back_to_moderation_list,
                ),
            ),

            state=model.ModerationPublicationStates.edit_preview,
            getter=self.moderation_publication_service.get_edit_preview_data,
            parse_mode="HTML",
        )

    def get_edit_text_menu_window(self) -> Window:
        """Новое меню редактирования текстовых элементов"""
        return Window(
            Multi(
                Const("✏️ <b>Редактирование текста</b>\n\n"),
                Const("📌 <b>Выберите, что изменить:</b>"),
                sep="",
            ),

            Column(
                Button(
                    Const("🔄 Перегенерировать всё"),
                    id="regenerate_all",
                    on_click=self.moderation_publication_service.handle_regenerate_text,
                ),
                Button(
                    Const("🔄 Перегенерировать с промптом"),
                    id="regenerate_with_prompt",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.regenerate_text),
                ),
                Button(
                    Const("📝 Изменить название"),
                    id="edit_title",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_title),
                ),
                Button(
                    Const("🏷 Изменить теги"),
                    id="edit_tags",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_tags),
                ),
                Button(
                    Const("📄 Изменить текст"),
                    id="edit_content",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_content),
                ),
            ),
            Button(
                Const("📄 ◀️ Назад к превью"),
                id="edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview),
            ),

            state=model.ModerationPublicationStates.edit_text_menu,
            parse_mode="HTML",
        )

    def get_regenerate_text_window(self) -> Window:
        """Новое окно для ввода дополнительного промпта при перегенерации"""
        return Window(
            Multi(
                Const("🔄 <b>Перегенерация с дополнительными указаниями</b>\n\n"),
                Const("💡 <b>Введите дополнительные пожелания:</b>\n"),
                Const(
                    "<i>Например: сделай текст короче, добавь больше эмоций, убери технические термины и т.д.</i>\n\n"),
                Case(
                    {
                        True: Format("📌 <b>Ваши указания:</b>\n<i>{regenerate_prompt}</i>"),
                        False: Const("💬 Ожидание ввода..."),
                    },
                    selector="has_regenerate_prompt"
                ),
                sep="",
            ),

            TextInput(
                id="regenerate_prompt_input",
                on_success=self.moderation_publication_service.handle_regenerate_text_with_prompt,
            ),
            Button(
                Const("📄 ◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_text_menu),
            ),

            state=model.ModerationPublicationStates.regenerate_text,
            getter=self.moderation_publication_service.get_regenerate_data,
            parse_mode="HTML",
        )

    def get_edit_title_window(self) -> Window:
        """Окно редактирования названия"""
        return Window(
            Multi(
                Const("📝 <b>Изменение названия</b>\n\n"),
                Format("Текущее: <b>{current_title}</b>\n\n"),
                Const("✍️ <b>Введите новое название:</b>\n"),
                Const("<i>Максимум 200 символов</i>"),
                sep="",
            ),

            TextInput(
                id="title_input",
                on_success=self.moderation_publication_service.handle_edit_title_save,
            ),

            Button(
                Const("Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview),
            ),

            state=model.ModerationPublicationStates.edit_title,
            getter=self.moderation_publication_service.get_edit_title_data,
            parse_mode="HTML",
        )

    def get_edit_tags_window(self) -> Window:
        """Окно редактирования тегов"""
        return Window(
            Multi(
                Const("🏷 <b>Изменение тегов</b>\n\n"),
                Case(
                    {
                        True: Format("Текущие теги: <b>{current_tags}</b>\n\n"),
                        False: Const("Теги отсутствуют\n\n"),
                    },
                    selector="has_tags"
                ),
                Const("✍️ <b>Введите теги через запятую:</b>\n"),
                Const("<i>Например: маркетинг, продажи, SMM</i>\n"),
                Const("<i>Оставьте пустым для удаления всех тегов</i>"),
                sep="",
            ),

            TextInput(
                id="tags_input",
                on_success=self.moderation_publication_service.handle_edit_tags_save,
            ),

            Button(
                Const("Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview),
            ),

            state=model.ModerationPublicationStates.edit_tags,
            getter=self.moderation_publication_service.get_edit_tags_data,
            parse_mode="HTML",
        )

    def get_edit_content_window(self) -> Window:
        """Окно редактирования основного текста"""
        return Window(
            Multi(
                Const("📄 <b>Изменение текста публикации</b>\n\n"),
                Format("Длина текущего текста: <b>{current_text_length}</b> символов\n\n"),
                Const("✍️ <b>Введите новый текст:</b>\n"),
                Const("<i>Минимум 50, максимум 4000 символов</i>\n"),
                Const("<i>Для просмотра текущего текста вернитесь назад</i>"),
                sep="",
            ),

            TextInput(
                id="content_input",
                on_success=self.moderation_publication_service.handle_edit_content_save,
            ),

            Button(
                Const("Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview),
            ),

            state=model.ModerationPublicationStates.edit_content,
            getter=self.moderation_publication_service.get_edit_content_data,
            parse_mode="HTML",
        )

    def get_edit_image_menu_window(self) -> Window:
        """Меню управления изображением при редактировании"""
        return Window(
            Multi(
                Const("🖼 <b>Управление изображением</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Const("✅ <b>Изображение присутствует</b>\n"),
                            Case(
                                {
                                    True: Const("📸 Тип: пользовательское\n"),
                                    False: Const("🎨 Тип: сгенерированное\n"),
                                },
                                selector="is_custom_image"
                            ),
                        ),
                        False: Const("❌ <b>Изображение отсутствует</b>\n"),
                    },
                    selector="has_image"
                ),
                Const("\n📌 <b>Выберите действие:</b>"),
                sep="",
            ),

            Column(
                Button(
                    Const("🎨 Сгенерировать новое"),
                    id="generate_image",
                    on_click=self.moderation_publication_service.handle_generate_new_image,
                ),
                Button(
                    Const("🎨 Сгенерировать с описанием"),
                    id="generate_image_prompt",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.generate_image),
                ),
                Button(
                    Const("📤 Загрузить изображение"),
                    id="upload_image",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.upload_image),
                ),
                Button(
                    Const("🗑 Удалить изображение"),
                    id="remove_image",
                    on_click=self.moderation_publication_service.handle_remove_image,
                    when="has_image",
                ),
            ),

            Button(
                Const("Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview),
            ),

            state=model.ModerationPublicationStates.edit_image_menu,
            getter=self.moderation_publication_service.get_image_menu_data,
            parse_mode="HTML",
        )

    def get_generate_image_window(self) -> Window:
        """Окно генерации изображения с промптом"""
        return Window(
            Multi(
                Const("🎨 <b>Генерация изображения</b>\n\n"),
                Const("💡 <b>Опишите желаемое изображение:</b>\n"),
                Const("<i>Например: минималистичная иллюстрация в синих тонах, деловой стиль</i>\n"),
                Const("<i>Или: абстрактная композиция с элементами технологий</i>\n\n"),
                Case(
                    {
                        True: Format("📌 <b>Ваше описание:</b>\n<i>{image_prompt}</i>"),
                        False: Const("💬 Ожидание ввода описания..."),
                    },
                    selector="has_image_prompt"
                ),
                sep="",
            ),

            TextInput(
                id="image_prompt_input",
                on_success=self.moderation_publication_service.handle_generate_image_with_prompt,
            ),

            Button(
                Const("Назад"),
                id="edit_image_menu",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_image_menu),
            ),

            state=model.ModerationPublicationStates.generate_image,
            getter=self.moderation_publication_service.get_image_prompt_data,
            parse_mode="HTML",
        )

    def get_upload_image_window(self) -> Window:
        """Окно загрузки собственного изображения"""
        return Window(
            Multi(
                Const("📤 <b>Загрузка изображения</b>\n\n"),
                Const("📸 <b>Отправьте изображение для публикации:</b>\n\n"),
                Const("✅ Поддерживаемые форматы: JPG, PNG, GIF\n"),
                Const("📏 Максимальный размер: 10 МБ\n"),
                Const("📐 Рекомендуемое соотношение: 16:9 или 1:1\n\n"),
                Const("<i>Изображение будет автоматически оптимизировано</i>"),
                sep="",
            ),

            MessageInput(
                func=self.moderation_publication_service.handle_image_upload,
                content_types=["photo"],
            ),

            Button(
                Const("Назад"),
                id="edit_image_menu",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_image_menu),
            ),

            state=model.ModerationPublicationStates.upload_image,
            parse_mode="HTML",
        )