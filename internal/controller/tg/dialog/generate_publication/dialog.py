from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, Select, Checkbox
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
            self.get_select_category_window(),
            self.get_input_text_window(),
            self.get_generation_window(),
            self.get_preview_window(),
            self.get_select_publish_location_window(),
        )

    def get_select_category_window(self) -> Window:
        """Окно выбора категории/рубрики для публикации"""
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Const("🏷 <b>Выберите рубрику</b>\n\n"),
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
                Const("❌ Вернуться в меню контента"),
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
                Const("✍️ <b>Опишите тему публикации</b>\n\n"),
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
            Back(Const("◀️ Назад")),

            state=model.GeneratePublicationStates.input_text,
            getter=self.generate_publication_service.get_input_text_data,
            parse_mode="HTML",
        )

    def get_generation_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n\n"),
                Format("📌 <b>Ваш текст:</b>\n<i>{input_text}</i>"),
                sep="",
            ),
            Button(
                Const("📄 Сгенерировать только текст"),
                id="text_only",
                on_click=self.generate_publication_service.handle_generate_text,
            ),
            Button(
                Const("📄 Сгенерировать текст + картинку"),
                id="with_image",
                on_click=self.generate_publication_service.handle_generate_text_with_image,
            ),

            state=model.GeneratePublicationStates.input_text,
            getter=self.generate_publication_service.get_input_text_data,
            parse_mode="HTML",
        )

    def get_preview_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Const("👀 <b>Предпросмотр публикации</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n"),
                Const("━━━━━━━━━━━━━━━━━━━━\n"),
                Format("<b>{publication_name}</b>\n\n"),
                Format("{publication_text}\n\n"),
                Case(
                    {
                        True: Format("🏷 Теги: {tags}\n"),
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

            # Вариант с обычными Checkbox (более стабильный)
            Column(
                Checkbox(
                    Const("✅ Telegram"),
                    Const("☐ Telegram"),
                    id="platform_telegram",
                    default=False,
                    on_state_changed=self.generate_publication_service.handle_platform_toggle,
                    when="telegram_available",
                ),
                Checkbox(
                    Const("✅ VKontakte"),
                    Const("☐ VKontakte"),
                    id="platform_vkontakte",
                    default=False,
                    on_state_changed=self.generate_publication_service.handle_platform_toggle,
                    when="vkontakte_available",
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
