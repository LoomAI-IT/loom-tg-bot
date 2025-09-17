# internal/controller/tg/dialog/generate_publication/dialog.py
from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, Select, Checkbox, Group, ManagedCheckbox
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia

from internal import interface, model


class GeneratePublicationDialog(interface.IGeneratePublicationDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            generate_publication_service: interface.IGeneratePublicationDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.generate_publication_service = generate_publication_service

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_select_category_window(),
            self.get_input_text_window(),
            self.get_choose_image_option_window(),
            self.get_image_generation_window(),
            self.get_preview_window(),
            self.get_select_publish_location_window(),
        )

    def get_select_category_window(self) -> Window:
        """Окно выбора категории/рубрики для публикации"""
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Const("🏷 <b>Шаг 1/5: Выберите рубрику</b>\n\n"),
                Case(
                    {
                        True: Const("📂 Доступные рубрики для публикации:"),
                        False: Multi(
                            Const("⚠️ <b>В организации нет созданных рубрик</b>\n\n"),
                            Const("Обратитесь к администратору для создания рубрик"),
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
                    on_click=self.generate_publication_service.handle_select_category,
                    when="has_categories",
                ),
            ),

            Button(
                Const("❌ Отмена"),
                id="cancel_to_content_menu",
                on_click=self.generate_publication_service.handle_go_to_content_menu,
            ),

            state=model.GeneratePublicationStates.select_category,
            getter=self.generate_publication_service.get_categories_data,
            parse_mode="HTML",
        )

    def get_input_text_window(self) -> Window:
        """Окно ввода текста для генерации"""
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Const("✍️ <b>Шаг 2/5: Опишите тему публикации</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n\n"),
                Const("💡 <b>Введите тему или описание публикации:</b>\n"),
                Const("<i>• Можете описать своими словами о чем должен быть пост\n"),
                Const("• Можете отправить голосовое сообщение\n"),
                Const("• ИИ создаст профессиональный текст на основе вашего описания</i>\n\n"),
                Case(
                    {
                        True: Format("📌 <b>Ваш текст:</b>\n<i>{input_text}</i>"),
                        False: Const("💬 Ожидание ввода текста или голосового сообщения..."),
                    },
                    selector="has_input_text"
                ),
                sep="",
            ),

            # Обработчик текстовых сообщений
            TextInput(
                id="text_input",
                on_success=self.generate_publication_service.handle_text_input,
            ),

            # Обработчик всех типов сообщений (включая голосовые)
            MessageInput(
                func=self.generate_publication_service.handle_voice_input,
                content_types=["voice", "audio"],
            ),

            Row(
                Button(
                    Const("➡️ Далее"),
                    id="next_to_image",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.choose_image_option),
                    when="has_input_text",
                ),
                Back(Const("◀️ Назад")),
            ),

            state=model.GeneratePublicationStates.input_text,
            getter=self.generate_publication_service.get_input_text_data,
            parse_mode="HTML",
        )

    def get_choose_image_option_window(self) -> Window:
        """Окно выбора опций изображения"""
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Const("🖼 <b>Шаг 3/5: Изображение для публикации</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n\n"),
                Const("🎨 <b>Выберите вариант работы с изображением:</b>"),
                sep="",
            ),

            Column(
                Button(
                    Const("🎨 Сгенерировать изображение с помощью ИИ"),
                    id="with_image",
                    on_click=self.generate_publication_service.handle_choose_with_image,
                ),
                Button(
                    Const("📄 Только текст (без изображения)"),
                    id="text_only",
                    on_click=self.generate_publication_service.handle_choose_text_only,
                ),
            ),

            Back(Const("◀️ Назад")),

            state=model.GeneratePublicationStates.choose_image_option,
            getter=self.generate_publication_service.get_image_option_data,
            parse_mode="HTML",
        )

    def get_image_generation_window(self) -> Window:
        """Окно генерации/загрузки изображения"""
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Const("🖼 <b>Шаг 4/5: Создание изображения</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n\n"),
                Case(
                    {
                        "generating": Multi(
                            Const("⏳ <b>Генерация изображения...</b>\n\n"),
                            Const("🎨 ИИ создает уникальное изображение для вашей публикации\n"),
                            Const("<i>Это может занять 10-30 секунд</i>"),
                        ),
                        "generated": Multi(
                            Const("✅ <b>Изображение сгенерировано!</b>\n\n"),
                            Const("🎯 <b>Что дальше?</b>"),
                        ),
                        "waiting": Multi(
                            Const("🎨 <b>Варианты создания изображения:</b>\n\n"),
                            Const("• Автоматическая генерация на основе текста\n"),
                            Const("• Генерация по вашему описанию\n"),
                            Const("• Загрузка готового изображения"),
                        ),
                        "waiting_prompt": Multi(
                            Const("✏️ <b>Введите описание для генерации изображения</b>\n\n"),
                            Const("💡 <i>Опишите, какое изображение вы хотите получить</i>"),
                        ),
                        "waiting_upload": Multi(
                            Const("📤 <b>Отправьте изображение</b>\n\n"),
                            Const("📸 <i>Загрузите фото для публикации</i>"),
                        ),
                        "uploaded": Multi(
                            Const("✅ <b>Изображение загружено!</b>\n\n"),
                            Const("📸 Ваше изображение готово к публикации"),
                        ),
                    },
                    selector="image_status"
                ),
                sep="",
            ),

            # Динамическое отображение изображения если оно есть
            DynamicMedia(
                selector="image_media",
                when="has_image",
            ),

            Column(
                Button(
                    Const("🎨 Автоматическая генерация"),
                    id="auto_generate",
                    on_click=self.generate_publication_service.handle_auto_generate_image,
                    when="show_generation_buttons",
                ),
                Button(
                    Const("✏️ Генерация по описанию"),
                    id="custom_prompt",
                    on_click=self.generate_publication_service.handle_request_custom_prompt,
                    when="show_generation_buttons",
                ),
                Button(
                    Const("📤 Загрузить свое изображение"),
                    id="upload_image",
                    on_click=self.generate_publication_service.handle_request_upload_image,
                    when="show_generation_buttons",
                ),
                Button(
                    Const("🔄 Перегенерировать"),
                    id="regenerate_image",
                    on_click=self.generate_publication_service.handle_regenerate_image,
                    when="can_regenerate",
                ),
                Button(
                    Const("🗑 Удалить изображение"),
                    id="delete_image",
                    on_click=self.generate_publication_service.handle_delete_image,
                    when="has_image",
                ),
            ),

            # Обработчик пользовательского промпта - всегда активен в этом окне
            TextInput(
                id="custom_prompt_input",
                on_success=self.generate_publication_service.handle_custom_prompt_image,
            ),

            # Обработчик загрузки изображений - всегда активен для фото
            MessageInput(
                func=self.generate_publication_service.handle_upload_image,
                content_types=["photo"],
            ),

            Row(
                Button(
                    Const("➡️ К предпросмотру"),
                    id="to_preview",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview),
                    when="can_continue",
                ),
                Back(Const("◀️ Назад"), when="not_generating"),
            ),

            state=model.GeneratePublicationStates.image_generation,
            getter=self.generate_publication_service.get_image_generation_data,
            parse_mode="HTML",
        )

    def get_preview_window(self) -> Window:
        """Окно предпросмотра публикации"""
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Const("👀 <b>Шаг 5/5: Предпросмотр публикации</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n"),
                Case(
                    {
                        True: Format("⏰ Публикация: <b>{publish_time}</b>\n\n"),
                        False: Const("⏰ Публикация: <b>Сразу после создания</b>\n\n"),
                    },
                    selector="has_scheduled_time"
                ),
                Const("━━━━━━━━━━━━━━━━━━━━\n"),
                Format("<b>{publication_title}</b>\n\n"),
                Format("{publication_text}\n\n"),
                Case(
                    {
                        True: Format("🏷 Теги: {tags_list}\n"),
                        False: Const(""),
                    },
                    selector="has_tags"
                ),
                Const("━━━━━━━━━━━━━━━━━━━━\n\n"),
                Const("📍 <b>Выберите действие:</b>"),
                sep="",
            ),

            # Динамическое отображение изображения
            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            Column(
                Row(
                    Button(
                        Const("✏️ Изменить текст"),
                        id="edit_text",
                        on_click=self.generate_publication_service.handle_edit_text,
                    ),
                    Button(
                        Const("🖼 Изменить изображение"),
                        id="edit_image",
                        on_click=self.generate_publication_service.handle_edit_image,
                        when="has_image",
                    ),
                ),
                Button(
                    Const("⏰ Настроить время публикации"),
                    id="schedule_time",
                    on_click=self.generate_publication_service.handle_schedule_time,
                ),
                Button(
                    Const("💾 Сохранить в черновики"),
                    id="save_draft",
                    on_click=self.generate_publication_service.handle_add_to_drafts,
                ),
                Button(
                    Const("📤 Отправить на модерацию"),
                    id="send_moderation",
                    on_click=self.generate_publication_service.handle_send_to_moderation,
                    when="requires_moderation",
                ),
                Button(
                    Const("🚀 Опубликовать"),
                    id="publish_now",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.select_publish_location),
                    when="can_publish_directly",
                ),
            ),

            Back(Const("◀️ Назад")),

            state=model.GeneratePublicationStates.preview,
            getter=self.generate_publication_service.get_preview_data,
            parse_mode="HTML",
        )

    def get_select_publish_location_window(self) -> Window:
        """Окно выбора платформ для публикации"""
        return Window(
            Multi(
                Const("🚀 <b>Публикация контента</b>\n\n"),
                Const("📍 <b>Выберите платформы для публикации:</b>\n\n"),
                Case(
                    {
                        True: Format("✅ Выбрано платформ: <b>{selected_count}</b>"),
                        False: Const("⚠️ <i>Выберите хотя бы одну платформу</i>"),
                    },
                    selector="has_selected_platforms"
                ),
                sep="",
            ),

            Column(
                Group(
                    ManagedCheckbox(
                        Const("✈️ Telegram"),
                        id="platform_telegram",
                        checked_text="✅",
                        unchecked_text="☐",
                        when="telegram_available",
                    ),
                    ManagedCheckbox(
                        Const("📷 Instagram"),
                        id="platform_instagram",
                        checked_text="✅",
                        unchecked_text="☐",
                        when="instagram_available",
                    ),
                    ManagedCheckbox(
                        Const("📘 VKontakte"),
                        id="platform_vkontakte",
                        checked_text="✅",
                        unchecked_text="☐",
                        when="vkontakte_available",
                    ),
                    ManagedCheckbox(
                        Const("🎬 YouTube Shorts"),
                        id="platform_youtube",
                        checked_text="✅",
                        unchecked_text="☐",
                        when="youtube_available",
                    ),
                    width=1,
                ),
            ),

            Row(
                Button(
                    Const("🚀 Опубликовать"),
                    id="confirm_publish",
                    on_click=self.generate_publication_service.handle_publish,
                    when="has_selected_platforms",
                ),
                Back(Const("◀️ Назад")),
            ),

            state=model.GeneratePublicationStates.select_publish_location,
            getter=self.generate_publication_service.get_publish_locations_data,
            parse_mode="HTML",
        )
