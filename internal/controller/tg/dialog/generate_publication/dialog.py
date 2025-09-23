from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, Select, Checkbox, Next
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia

from internal import interface, model


class GeneratePublicationDialog(interface.IGeneratePublicationDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            generate_publication_service: interface.IGeneratePublicationService,
            generate_publication_getter: interface.IGeneratePublicationGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.generate_publication_service = generate_publication_service
        self.generate_publication_getter = generate_publication_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_select_category_window(),
            self.get_input_text_window(),
            self.get_generation_window(),
            self.get_preview_window(),
            self.get_edit_text_menu_window(),
            self.get_regenerate_text_window(),
            self.get_edit_title_window(),
            self.get_edit_tags_window(),
            self.get_edit_content_window(),
            self.get_image_menu_window(),
            self.get_generate_image_window(),
            self.get_upload_image_window(),
            self.get_social_network_select_window()
        )

    def get_select_category_window(self) -> Window:
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
            getter=self.generate_publication_getter.get_categories_data,
            parse_mode="HTML",
        )

    def get_input_text_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Const("✍️ <b>Опишите тему публикации</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n\n"),
                # Text input error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст не может быть пустым\n\n"),
                        False: Const(""),
                    },
                    selector="has_void_input_text"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст слишком короткий (минимум 10 символов)\n\n"),
                        False: Const(""),
                    },
                    selector="has_small_input_text"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст слишком длинный (максимум 2000 символов)\n\n"),
                        False: Const(""),
                    },
                    selector="has_big_input_text"
                ),
                # Voice input error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Отправьте голосовое сообщение или аудиофайл\n\n"),
                        False: Const(""),
                    },
                    selector="has_invalid_voice_type"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Голосовое сообщение слишком длинное (максимум 5 минут)\n\n"),
                        False: Const(""),
                    },
                    selector="has_long_voice_duration"
                ),
                Case(
                    {
                        True: Const(
                            "⚠️ <b>Ошибка:</b> Не удалось распознать речь. Попробуйте записать заново или введите текст\n\n"),
                        False: Const(""),
                    },
                    selector="has_voice_recognition_error"
                ),
                Case(
                    {
                        True: Const(
                            "⚠️ <b>Ошибка:</b> В голосовом сообщении не распознан текст. Попробуйте говорить четче\n\n"),
                        False: Const(""),
                    },
                    selector="has_empty_voice_text"
                ),
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

            TextInput(
                id="text_input",
                on_success=self.generate_publication_service.handle_text_input,
            ),

            MessageInput(
                func=self.generate_publication_service.handle_voice_input,
                content_types=["voice", "audio"],
            ),

            Row(
                Next(
                    Const("➡️ Далее"),
                    when="has_input_text"
                ),
                Back(Const("◀️ Назад")),
            ),

            state=model.GeneratePublicationStates.input_text,
            getter=self.generate_publication_getter.get_input_text_data,
            parse_mode="HTML",
        )

    def get_generation_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Создание новой публикации</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n\n"),
                Format("📌 <b>Ваш текст:</b>\n<i>{input_text}</i>\n\n"),
                Const("🎯 <b>Выберите тип контента:</b>"),
                sep="",
            ),

            Column(
                Button(
                    Const("📄 Только текст"),
                    id="text_only",
                    on_click=self.generate_publication_service.handle_generate_text,
                ),
                Button(
                    Const("🖼 Текст + изображение"),
                    id="with_image",
                    on_click=self.generate_publication_service.handle_generate_text_with_image,
                ),
            ),

            Back(Const("◀️ Назад")),

            state=model.GeneratePublicationStates.generation,
            getter=self.generate_publication_getter.get_input_text_data,
            parse_mode="HTML",
        )

    def get_preview_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Предпросмотр публикации</b>\n\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n"),
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
                # Добавляем информацию о множественных изображениях
                Case(
                    {
                        True: Format("\n🖼 Изображение {current_image_index} из {total_images}"),
                        False: Const(""),
                    },
                    selector="has_multiple_images"
                ),
                Const("\n━━━━━━━━━━━━━━━━━━━━"),
                sep="",
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            # Добавляем кнопки навигации по изображениям
            Row(
                Button(
                    Const("⬅️"),
                    id="prev_image",
                    on_click=self.generate_publication_service.handle_prev_image,
                    when="has_multiple_images",
                ),
                Button(
                    Const("➡️"),
                    id="next_image",
                    on_click=self.generate_publication_service.handle_next_image,
                    when="has_multiple_images",
                ),
                when="has_multiple_images",
            ),

            Column(
                Row(
                    Button(
                        Const("✏️ Текст"),
                        id="edit_text_menu",
                        on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu),
                    ),
                    Button(
                        Const("🖼 Изображение"),
                        id="edit_image_menu",
                        on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu),
                    ),
                ),
                Button(
                    Const("💾 В черновики"),
                    id="save_draft",
                    on_click=self.generate_publication_service.handle_add_to_drafts,
                ),
                Button(
                    Const("📤 На модерацию"),
                    id="send_moderation",
                    on_click=self.generate_publication_service.handle_send_to_moderation,
                    when="requires_moderation",
                ),
                Button(
                    Const("🚀 Опубликовать"),
                    id="publish_now",
                    on_click=self.generate_publication_service.handle_publish_now,
                    when="can_publish_directly",
                ),
            ),

            Button(
                Const("❌ Отмена"),
                id="cancel",
                on_click=self.generate_publication_service.handle_go_to_content_menu,
            ),

            state=model.GeneratePublicationStates.preview,
            getter=self.generate_publication_getter.get_preview_data,
            parse_mode="HTML",
        )

    def get_edit_text_menu_window(self) -> Window:
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
                    on_click=self.generate_publication_service.handle_regenerate_text,
                ),
                Button(
                    Const("🔄 Перегенерировать с промптом"),
                    id="regenerate_with_prompt",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.regenerate_text),
                ),
                Button(
                    Const("📝 Изменить название"),
                    id="edit_title",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_title),
                ),
                Button(
                    Const("🏷 Изменить теги"),
                    id="edit_tags",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_tags),
                ),
                Button(
                    Const("📄 Изменить текст"),
                    id="edit_content",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_content),
                ),
            ),
            Button(
                Const("📄 ◀️ Назад к превью"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview),
            ),

            state=model.GeneratePublicationStates.edit_text_menu,
            parse_mode="HTML",
        )

    def get_regenerate_text_window(self) -> Window:
        return Window(
            Multi(
                Const("🔄 <b>Перегенерация с дополнительными указаниями</b>\n\n"),
                # Показываем состояние загрузки если регенерируем
                Case(
                    {
                        True: Multi(
                            Format("📌 <b>Ваши указания:</b>\n<i>{regenerate_prompt}</i>\n\n"),
                            Const("⏳ <b>Перегенерирую текст...</b>\n"),
                            Const("Это может занять время. Пожалуйста, ожидайте."),
                        ),
                        False: Multi(
                            # Error messages только если не регенерируем
                            Case(
                                {
                                    True: Const("⚠️ <b>Ошибка:</b> Укажите дополнительные пожелания\n\n"),
                                    False: Const(""),
                                },
                                selector="has_void_regenerate_prompt"
                            ),
                            Case(
                                {
                                    True: Const("⚠️ <b>Ошибка:</b> Указания слишком короткие (минимум 5 символов)\n\n"),
                                    False: Const(""),
                                },
                                selector="has_small_regenerate_prompt"
                            ),
                            Case(
                                {
                                    True: Const(
                                        "⚠️ <b>Ошибка:</b> Указания слишком длинные (максимум 500 символов)\n\n"),
                                    False: Const(""),
                                },
                                selector="has_big_regenerate_prompt"
                            ),
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
                        ),
                    },
                    selector="is_regenerating_text"
                ),
                sep="",
            ),

            TextInput(
                id="regenerate_prompt_input",
                on_success=self.generate_publication_service.handle_regenerate_text_with_prompt,
            ),

            Button(
                Const("📄 ◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu),
                when="~is_regenerating_text",  # Отключаем кнопку во время регенерации
            ),

            state=model.GeneratePublicationStates.regenerate_text,
            getter=self.generate_publication_getter.get_regenerate_data,
            parse_mode="HTML",
        )

    def get_edit_title_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Изменение названия</b>\n\n"),
                Format("Текущее: <b>{publication_name}</b>\n\n"),
                # Add error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Название не может быть пустым\n\n"),
                        False: Const(""),
                    },
                    selector="has_void_title"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Название слишком длинное (максимум 200 символов)\n\n"),
                        False: Const(""),
                    },
                    selector="has_big_title"
                ),
                Const("✍️ <b>Введите новое название:</b>"),
                sep="",
            ),

            TextInput(
                id="title_input",
                on_success=self.generate_publication_service.handle_edit_title_save,
            ),

            Button(
                Const("📄 ◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu),
            ),

            state=model.GeneratePublicationStates.edit_title,
            getter=self.generate_publication_getter.get_edit_title_data,
            parse_mode="HTML",
        )

    def get_edit_tags_window(self) -> Window:
        """Окно редактирования тегов"""
        return Window(
            Multi(
                Const("🏷 <b>Изменение тегов</b>\n\n"),
                Format("Текущие теги: <b>{publication_tags}</b>\n\n"),
                # Add error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Слишком много тегов (максимум 10)\n\n"),
                        False: Const(""),
                    },
                    selector="has_too_many_tags"
                ),
                Const("✍️ <b>Введите теги через запятую:</b>\n"),
                Const("<i>Например: маркетинг, продажи, SMM</i>"),
                sep="",
            ),

            TextInput(
                id="tags_input",
                on_success=self.generate_publication_service.handle_edit_tags_save,
            ),

            Button(
                Const("📄 ◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu),
            ),

            state=model.GeneratePublicationStates.edit_tags,
            getter=self.generate_publication_getter.get_edit_tags_data,
            parse_mode="HTML",
        )

    def get_edit_content_window(self) -> Window:
        return Window(
            Multi(
                Const("📄 <b>Изменение текста публикации</b>\n\n"),
                # Add error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст не может быть пустым\n\n"),
                        False: Const(""),
                    },
                    selector="has_void_content"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст слишком короткий (минимум 50 символов)\n\n"),
                        False: Const(""),
                    },
                    selector="has_small_content"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст слишком длинный (максимум 4000 символов)\n\n"),
                        False: Const(""),
                    },
                    selector="has_big_content"
                ),
                Const("✍️ <b>Введите новый текст:</b>\n"),
                Const("<i>Текущий текст показан в предыдущем окне</i>"),
                sep="",
            ),

            TextInput(
                id="content_input",
                on_success=self.generate_publication_service.handle_edit_content_save,
            ),

            Button(
                Const("📄 ◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu),
            ),

            state=model.GeneratePublicationStates.edit_content,
            getter=self.generate_publication_getter.get_edit_content_data,
            parse_mode="HTML",
        )

    def get_image_menu_window(self) -> Window:
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
                    Const("🎨 Сгенерировать новое"),
                    id="generate_image",
                    on_click=self.generate_publication_service.handle_generate_new_image,
                ),
                Button(
                    Const("🎨 Сгенерировать с промптом"),
                    id="generate_image_prompt",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.generate_image),
                ),
                Button(
                    Const("📤 Загрузить своё"),
                    id="upload_image",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.upload_image),
                ),
                Button(
                    Const("🗑 Удалить изображение"),
                    id="remove_image",
                    on_click=self.generate_publication_service.handle_remove_image,
                    when="has_image",
                ),
            ),

            Button(
                Const("📄 ◀️ Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview),
            ),

            state=model.GeneratePublicationStates.image_menu,
            getter=self.generate_publication_getter.get_image_menu_data,
            parse_mode="HTML",
        )

    def get_generate_image_window(self) -> Window:
        return Window(
            Multi(
                Const("🎨 <b>Генерация изображения</b>\n\n"),
                # Показываем состояние загрузки если генерируем
                Case(
                    {
                        True: Multi(
                            Format("📌 <b>Ваше описание:</b>\n<i>{image_prompt}</i>\n\n"),
                            Const("⏳ <b>Генерирую изображение...</b>\n"),
                            Const("Это может занять время. Пожалуйста, ожидайте."),
                        ),
                        False: Multi(
                            # Error messages только если не генерируем
                            Case(
                                {
                                    True: Const("⚠️ <b>Ошибка:</b> Описание изображения не может быть пустым\n\n"),
                                    False: Const(""),
                                },
                                selector="has_void_image_prompt"
                            ),
                            Case(
                                {
                                    True: Const("⚠️ <b>Ошибка:</b> Описание слишком короткое (минимум 5 символов)\n\n"),
                                    False: Const(""),
                                },
                                selector="has_small_image_prompt"
                            ),
                            Case(
                                {
                                    True: Const(
                                        "⚠️ <b>Ошибка:</b> Описание слишком длинное (максимум 500 символов)\n\n"),
                                    False: Const(""),
                                },
                                selector="has_big_image_prompt"
                            ),
                            Const("💡 <b>Опишите желаемое изображение:</b>\n"),
                            Const("<i>Например: минималистичная иллюстрация в синих тонах, деловой стиль</i>\n\n"),
                            Case(
                                {
                                    True: Format("📌 <b>Ваше описание:</b>\n<i>{image_prompt}</i>"),
                                    False: Const("💬 Ожидание ввода..."),
                                },
                                selector="has_image_prompt"
                            ),
                        ),
                    },
                    selector="is_generating_image"
                ),
                sep="",
            ),

            TextInput(
                id="image_prompt_input",
                on_success=self.generate_publication_service.handle_generate_image_with_prompt,
            ),

            Button(
                Const("📄 ◀️ Назад"),
                id="image_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu),
                when="~is_generating_image",  # Отключаем кнопку во время генерации
            ),

            state=model.GeneratePublicationStates.generate_image,
            getter=self.generate_publication_getter.get_image_prompt_data,
            parse_mode="HTML",
        )

    def get_upload_image_window(self) -> Window:
        return Window(
            Multi(
                Const("📤 <b>Загрузка изображения</b>\n\n"),
                # Add error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Пожалуйста, отправьте изображение (не другой тип файла)\n\n"),
                        False: Const(""),
                    },
                    selector="has_invalid_image_type"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Файл слишком большой (максимум 10 МБ)\n\n"),
                        False: Const(""),
                    },
                    selector="has_big_image_size"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Не удалось обработать изображение, попробуйте другое\n\n"),
                        False: Const(""),
                    },
                    selector="has_image_processing_error"
                ),
                Const("📸 <b>Отправьте изображение:</b>\n"),
                Const("<i>Поддерживаются форматы: JPG, PNG, GIF</i>\n"),
                Const("<i>Максимальный размер: 10 МБ</i>"),
                sep="",
            ),

            MessageInput(
                func=self.generate_publication_service.handle_image_upload,
            ),

            Button(
                Const("📄 ◀️ Назад"),
                id="image_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu),
            ),

            state=model.GeneratePublicationStates.upload_image,
            getter=self.generate_publication_getter.get_upload_image_data,
            parse_mode="HTML",
        )

    def get_social_network_select_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Выбор социальных сетей</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Нет подключенных социальных сетей!</b>\n\n"),
                            Const(
                                "🔗 <i>Для публикации постов необходимо подключить хотя бы одну социальную сеть в настройках организации.</i>\n\n"),
                            Const("Обратитесь к администратору для подключения социальных сетей."),
                        ),
                        False: Multi(
                            Const("📋 <b>Доступные социальные сети:</b>\n\n"),
                            Case(
                                {
                                    True: Const("📺 Telegram - <b>подключен</b>\n"),
                                    False: Const("📺 Telegram - <b>не подключен</b>\n"),
                                },
                                selector="telegram_connected"
                            ),
                            Case(
                                {
                                    True: Const("🔗 VKontakte - <b>подключен</b>\n\n"),
                                    False: Const("🔗 VKontakte - <b>не подключен</b>\n\n"),
                                },
                                selector="vkontakte_connected"
                            ),
                            Const("✅ <b>Выберите, где опубликовать:</b>"),
                        ),
                    },
                    selector="no_connected_networks"
                ),
                sep="",
            ),

            # Чекбоксы для выбора платформ (только для подключенных)
            Column(
                Checkbox(
                    Const("✅ Telegram"),
                    Const("❌ Telegram"),
                    id="telegram_checkbox",
                    default=False,
                    on_state_changed=self.generate_publication_service.handle_toggle_social_network,
                    when="telegram_connected",
                ),
                Checkbox(
                    Const("✅ VKontakte"),
                    Const("❌ VKontakte"),
                    id="vkontakte_checkbox",
                    default=False,
                    on_state_changed=self.generate_publication_service.handle_toggle_social_network,
                    when="vkontakte_connected",
                ),
                when="has_available_networks",
            ),

            # Кнопки действий
            Row(
                Button(
                    Const("🚀 Опубликовать"),
                    id="publish_with_networks",
                    on_click=self.generate_publication_service.handle_publish_with_selected_networks,
                    when="has_available_networks",
                ),
                Button(
                    Const("◀️ Назад"),
                    id="back_to_preview",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview),
                ),
            ),

            # Кнопка назад для случая когда нет доступных сетей
            Button(
                Const("◀️ Назад к превью"),
                id="back_to_preview_no_networks",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview),
                when="no_connected_networks",
            ),

            state=model.GeneratePublicationStates.social_network_select,
            getter=self.generate_publication_getter.get_social_network_select_data,
            parse_mode="HTML",
        )