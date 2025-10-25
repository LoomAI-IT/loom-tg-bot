from aiogram import F
from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Back, Select, Checkbox
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia
from sulguk import SULGUK_PARSE_MODE

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
            self.get_image_menu_window(),
            self.get_edit_text_window(),
            self.get_upload_image_window(),
            self.get_combine_images_choice_window(),
            self.get_combine_images_upload_window(),
            self.get_combine_images_prompt_window(),
            self.get_combine_images_confirm_window(),
            self.get_social_network_select_window(),
            self.get_text_too_long_alert_window(),
            self.get_publication_success_window()  # Новое окно
        )

    def get_select_category_window(self) -> Window:
        return Window(
            Multi(
                Const("🎯 <b>Выберите рубрику для генерации контента</b><br>"),
                Case(
                    {
                        True: Const("📋 <b>Доступные рубрики:</b>"),
                        False: Multi(
                            Const("🚫 <b>Рубрики не созданы</b><br>"),
                            Const("💡 <i>Обратитесь к администратору для создания рубрик</i>"),
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
                Const("Создать рубрику"),
                id="go_to_main_menu",
                on_click=self.generate_publication_service.go_to_create_category,
            ),

            Button(
                Const("◀️ Назад"),
                id="cancel_to_content_menu",
                on_click=self.generate_publication_service.handle_go_to_content_menu,
            ),

            state=model.GeneratePublicationStates.select_category,
            getter=self.generate_publication_getter.get_categories_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_input_text_window(self) -> Window:
        return Window(
            Case(
                {
                    False: Multi(
                        Const("📝 <b>Создание контента</b><br><br>"),
                        Format("{category_hint}<br><br>"),
                        Const("💬 <i>Отправьте текст или голосовое сообщение — я превращу их в готовый контент</i>"),
                        Case(
                            {
                                True: Format("<br>📄 <b>Ваш текст:</b><br><i>{input_text}</i>"),
                                False: Const(""),
                            },
                            selector="has_input_text"
                        ),
                        # Text input error messages
                        Case(
                            {
                                True: Const("<br>❌ <b>Ошибка:</b> Текст не может быть пустым"),
                                False: Const(""),
                            },
                            selector="has_void_input_text"
                        ),
                        Case(
                            {
                                True: Const("<br>📏 <b>Слишком короткий текст</b><br><i>Минимум 10 символов</i>"),
                                False: Const(""),
                            },
                            selector="has_small_input_text"
                        ),
                        Case(
                            {
                                True: Const("<br>📏 <b>Слишком длинный текст</b><br><i>Максимум 2000 символов</i>"),
                                False: Const(""),
                            },
                            selector="has_big_input_text"
                        ),
                        # Voice input error messages
                        Case(
                            {
                                True: Const(
                                    "<br>🎤 <b>Неверный формат</b><br><i>Отправьте голосовое сообщение, аудиофайл или текст</i>"),
                                False: Const(""),
                            },
                            selector="has_invalid_content_type"
                        ),
                        sep="",
                    ),
                    True: Const("🔄 Распознавание речи...")
                },
                selector="voice_transcribe"
            ),

            MessageInput(
                func=self.generate_publication_service.handle_generate_publication_prompt_input,
            ),

            Row(
                # Next(
                #     Const("▶️ Далее"),
                #     when="has_input_text"
                # ),
                Back(Const("◀️ Назад")),
            ),

            state=model.GeneratePublicationStates.input_text,
            getter=self.generate_publication_getter.get_input_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_generation_window(self) -> Window:
        return Window(
            Multi(
                Const("🎨 <b>Настройка публикации</b><br>"),
                Const("📸 <i>Хотите добавить изображение к тексту?</i>"),
                sep="",
            ),

            Column(
                Button(
                    Const("📝 Только текст"),
                    id="text_only",
                    on_click=self.generate_publication_service.handle_generate_text,
                ),
                Button(
                    Const("🖼️ С картинкой"),
                    id="with_image",
                    on_click=self.generate_publication_service.handle_generate_text_with_image,
                ),
            ),

            Back(Const("◀️ Назад")),

            state=model.GeneratePublicationStates.generation,
            getter=self.generate_publication_getter.get_input_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_preview_window(self) -> Window:
        return Window(
            Multi(
                Const("👁️ <b>Предварительный просмотр</b><br><br>"),
                Format("{publication_text}"),
                Case(
                    {
                        True: Format("<br><br>🖼️ <b>Изображение {current_image_index} из {total_images}</b>"),
                        False: Const(""),
                    },
                    selector="has_multiple_images"
                ),
                sep="",
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            # Добавляем кнопки навигации по изображениям
            Row(
                Button(
                    Const("⬅️ Предыдущая"),
                    id="prev_image",
                    on_click=self.generate_publication_service.handle_prev_image,
                    when="has_multiple_images",
                ),
                Button(
                    Const("➡️ Следующая"),
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
                        on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu,
                                                             ShowMode.EDIT),
                    ),
                    Button(
                        Const("🎨 Картинка"),
                        id="edit_image_menu",
                        on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu, ShowMode.EDIT),
                    ),
                ),
                Button(
                    Const("📝 Добавить в черновики"),
                    id="save_draft",
                    on_click=self.generate_publication_service.handle_add_to_drafts,
                ),
                Button(
                    Const("👁️‍🗨️ Отправить на модерацию"),
                    id="send_moderation",
                    on_click=self.generate_publication_service.handle_send_to_moderation,
                    when="requires_moderation",
                ),
                Button(
                    Const("🌐 Выбрать место публикации"),
                    id="select_social_network",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.social_network_select,
                                                         ShowMode.EDIT),
                    when="can_publish_directly",
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
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_text_menu_window(self) -> Window:
        return Window(
            Multi(
                Case(
                    {
                        False: Multi(
                            Const("✏️ <b>Редактирование текста</b><br>"),
                            Format("<blockquote>{publication_text}</blockquote><br>"),
                            Const("🎯 <b>КАК ИЗМЕНИТЬ ТЕКСТ:</b><br><br>"),
                            Const("💬 <b>Напишите сообщение</b><br>"),
                            Const("<i>Укажите, что нужно изменить</i><br>"),
                            Const("🎤 <b>Запишите голосовое</b><br>"),
                            Const("<i>Опишите нужные правки голосом</i><br><br>"),
                            Const("🔘 <b>Или используйте кнопки ниже</b>"),
                        ),
                        True: Case(
                            {
                                True: Multi(
                                    Format("📝 <b>Ваши указания:</b><br><code>{regenerate_prompt}</code><br>"),
                                    Const("⏳ <b>Перегенерирую текст...</b><br>"),
                                    Const("🕐 <i>Это может занять время. Пожалуйста, подождите.</i>"),
                                ),
                                False: Multi(
                                    Const("⏳ <b>Перегенерирую текст...</b><br>"),
                                    Const("🕐 <i>Это может занять время. Пожалуйста, подождите.</i>"),
                                ),
                            },
                            selector="has_regenerate_prompt"
                        )
                    },
                    selector="is_regenerating_text"
                ),
                # Голосовое распознавание
                Case(
                    {
                        True: Const("<br>🔄 <b>Распознаю голосовое сообщение...</b>"),
                        False: Const(""),
                    },
                    selector="voice_transcribe"
                ),
                # Ошибки ввода текста
                Case(
                    {
                        True: Const("<br>❌ <b>Ошибка:</b> Указания не могут быть пустыми"),
                        False: Const(""),
                    },
                    selector="has_void_regenerate_prompt"
                ),
                Case(
                    {
                        True: Const("<br>📏 <b>Слишком короткие указания</b><br><i>Минимум 10 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_small_regenerate_prompt"
                ),
                Case(
                    {
                        True: Const("<br>📏 <b>Слишком длинные указания</b><br><i>Максимум 1000 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_big_regenerate_prompt"
                ),
                Case(
                    {
                        True: Const("<br>🎤 <b>Неверный формат</b><br><i>Отправьте текст, голосовое сообщение или аудиофайл</i>"),
                        False: Const(""),
                    },
                    selector="has_invalid_content_type"
                ),
                sep="",
            ),

            MessageInput(
                func=self.generate_publication_service.handle_regenerate_text_prompt_input,
            ),

            Column(
                Button(
                    Const("🔄 Перегенерировать текст"),
                    id="regenerate_all",
                    on_click=self.generate_publication_service.handle_regenerate_text,
                    when=~F["is_regenerating_text"]
                ),
                Button(
                    Const("✍️ Написать свой текст"),
                    id="edit_content",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text, ShowMode.EDIT),
                    when=~F["is_regenerating_text"]
                ),
            ),
            Button(
                Const("◀️ Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview, ShowMode.EDIT),
                when=~F["is_regenerating_text"]
            ),

            state=model.GeneratePublicationStates.edit_text_menu,
            getter=self.generate_publication_getter.get_edit_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_text_window(self) -> Window:
        return Window(
            Multi(
                Const("✍️ <b>Написать свой текст</b><br>"),
                Format("<blockquote>{publication_text}</blockquote><br>"),
                Const("✏️ <b>НАПИШИТЕ НОВЫЙ ТЕКСТ:</b><br>"),
                Const("<i>Отправьте готовый текст публикации, который заменит текущий</i><br><br>"),
                # Error messages
                Case(
                    {
                        True: Const("<br><br>❌ <b>Ошибка:</b> Текст не может быть пустым"),
                        False: Const(""),
                    },
                    selector="has_void_text"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком короткий текст</b><br><i>Минимум 50 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_small_text"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком длинный текст</b><br><i>Максимум 4000 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_big_text"
                ),
                sep="",
            ),

            TextInput(
                id="text_input",
                on_success=self.generate_publication_service.handle_edit_text,
            ),

            Button(
                Const("◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu, ShowMode.EDIT),
            ),

            state=model.GeneratePublicationStates.edit_text,
            getter=self.generate_publication_getter.get_edit_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_image_menu_window(self) -> Window:
        return Window(
            Multi(
                Case(
                    {
                        False: Const(""),
                        True: Multi(
                            Const("⏳ <b>Генерирую изображение...</b><br>"),
                            Const("🕐 <i>Это может занять время. Пожалуйста, подождите.</i>"),
                        ),
                    },
                    selector="is_generating_image"
                ),
                sep="",
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            Multi(
                Case(
                    {
                        True: Multi(
                            Const("🎯 <b>ЧТО МОЖНО СДЕЛАТЬ:</b><br><br>"),
                            Const("💬 <b>Написать текст или 🎤 записать голосовое</b><br>"),
                            Const("<i>Картинка изменится с учётом ваших указаний</i><br>"),
                            Const("🔘 <b>Нажать кнопку \"🎨 Сгенерировать картинку\"</b><br>"),
                            Const("<i>ИИ создаст новый вариант на основе текста публикации</i><br><br>"),
                            Const("📝 <b>Что можно указать в описании:</b><br>"),
                            Const("• Изменения цветов и освещения<br>"),
                            Const("• Добавление или удаление объектов<br>"),
                            Const("• Изменение стиля или настроения<br>"),
                            Const("• Правки композиции и фона"),
                        ),
                        False: Multi(
                            Const("🎯 <b>ЧТО МОЖНО СДЕЛАТЬ:</b><br><br>"),
                            Const("🔘 <b>Нажать кнопку \"🎨 Сгенерировать картинку\"</b><br>"),
                            Const("<i>ИИ создаст картинку на основе текста публикации</i><br><br>"),
                            Const("💬 <b>Написать текст или 🎤 записать голосовое</b><br>"),
                            Const("<i>Картинка создастся с учётом вашего описания</i><br>"),
                            Const("📝 <b>Что можно указать в описании:</b><br>"),
                            Const("• 👥 Объекты и персонажи<br>"),
                            Const("• 🎭 Стиль и настроение<br>"),
                            Const("• 🌍 Фон и окружение<br>"),
                            Const("• ✨ Детали и освещение"),
                        ),
                    },
                    selector="has_image"
                ),
                Case(
                    {
                        True: Const("<br><br>🔄 <b>Распознаю голосовое сообщение...</b>"),
                        False: Const(""),
                    },
                    selector="voice_transcribe"
                ),
                Case(
                    {
                        True: Const("<br><br>❌ <b>Ошибка:</b> Описание не может быть пустым"),
                        False: Const(""),
                    },
                    selector="has_void_image_prompt"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком короткое описание</b><br><i>Минимум 10 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_small_image_prompt"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком длинное описание</b><br><i>Максимум 1000 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_big_image_prompt"
                ),
                Case(
                    {
                        True: Const("<br><br>🎤 <b>Неверный формат</b><br><i>Отправьте текст, голосовое сообщение или аудиофайл</i>"),
                        False: Const(""),
                    },
                    selector="has_invalid_content_type"
                ),
                when=~F["is_generating_image"],
                sep="",
            ),

            MessageInput(
                func=self.generate_publication_service.handle_generate_image_prompt_input,
            ),

            Column(
                Button(
                    Const("🎨 Сгенерировать картинку"),
                    id="generate_image",
                    on_click=self.generate_publication_service.handle_generate_new_image,
                ),
                Button(
                    Const("📷 Использовать своё фото"),
                    id="upload_image",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.upload_image, ShowMode.EDIT),
                ),
                Button(
                    Const("📐 Объединить изображения"),
                    id="combine_images",
                    on_click=self.generate_publication_service.handle_combine_images_start,
                ),
                Button(
                    Const("🗑️ Удалить изображение"),
                    id="remove_image",
                    on_click=self.generate_publication_service.handle_remove_image,
                    when="has_image",
                ),
                when=~F["is_generating_image"]
            ),

            Button(
                Const("◀️ Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview, ShowMode.EDIT),
                when=~F["is_generating_image"]
            ),

            state=model.GeneratePublicationStates.image_menu,
            getter=self.generate_publication_getter.get_image_menu_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_upload_image_window(self) -> Window:
        return Window(
            Multi(
                Const("📷 <b>Загрузка изображения</b><br>"),
                Const("📤 <i>Отправьте своё изображение</i>"),
                # Add error messages
                Case(
                    {
                        True: Const(
                            "<br>❌ <b>Неверный формат файла</b><br><i>Отправьте изображение</i>"),
                        False: Const(""),
                    },
                    selector="has_invalid_image_type"
                ),
                Case(
                    {
                        True: Const("<br>📁 <b>Файл слишком большой</b><br><i>Максимум 10 МБ</i>"),
                        False: Const(""),
                    },
                    selector="has_big_image_size"
                ),
                Case(
                    {
                        True: Const(
                            "<br>⚠️ <b>Ошибка обработки</b><br><i>Не удалось обработать изображение, попробуйте другое</i>"),
                        False: Const(""),
                    },
                    selector="has_image_processing_error"
                ),
                sep="",
            ),

            MessageInput(
                func=self.generate_publication_service.handle_image_upload,
            ),

            Button(
                Const("◀️ Назад"),
                id="image_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu, ShowMode.EDIT),
            ),

            state=model.GeneratePublicationStates.upload_image,
            getter=self.generate_publication_getter.get_upload_image_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_social_network_select_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Выбор платформы для публикации</b><br>"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Социальные сети не подключены</b><br>"),
                            Const(
                                "🔗 <i>Для публикации необходимо подключить хотя бы одну социальную сеть в настройках организации</i><br>"),
                            Const("💡 <b>Обратитесь к администратору для настройки подключений</b>"),
                        ),
                        False: Multi(
                            Const("📱 <b>Выберите платформы для публикации:</b><br>"),
                            Const("💡 <i>Можно выбрать несколько вариантов</i>"),
                        ),
                    },
                    selector="no_connected_networks"
                ),
                sep="",
            ),

            # Чекбоксы для выбора платформ (только для подключенных)
            Column(
                Checkbox(
                    Const("✅ 📱 Telegram"),
                    Const("⬜ 📱 Telegram"),
                    id="telegram_checkbox",
                    default=False,
                    on_state_changed=self.generate_publication_service.handle_toggle_social_network,
                    when="telegram_connected",
                ),
                Checkbox(
                    Const("✅ 🔵 ВКонтакте"),
                    Const("⬜ 🔵 ВКонтакте"),
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
                    Const("◀️ Назад"),
                    id="back_to_preview",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview, ShowMode.EDIT),
                ),
            ),

            state=model.GeneratePublicationStates.social_network_select,
            getter=self.generate_publication_getter.get_social_network_select_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_text_too_long_alert_window(self) -> Window:
        return Window(
            Multi(
                Const("⚠️ <b>Текст слишком длинный</b><br><br>"),
                Format("📏 <b>Текущая длина:</b> {current_text_length} символов<br>"),
                Format("📊 <b>Максимум с фото:</b> {max_length_with_image} символов<br><br>"),
                Const("💡 <b>Что делать?</b><br>"),
                Const("• <b>Сжать текст</b> — ИИ автоматически сократит до нужной длины<br>"),
                Const("• <b>Отказаться от фото</b> — публикация будет только с текстом"),
                sep="",
            ),

            Column(
                Button(
                    Const("📝 Сжать текст"),
                    id="compress_text",
                    on_click=self.generate_publication_service.handle_compress_text,
                ),
                Button(
                    Const("🗑️ Отказаться от фото"),
                    id="remove_photo",
                    on_click=self.generate_publication_service.handle_remove_photo_from_long_text,
                ),
            ),

            Button(
                Const("📋 К меню контента"),
                id="go_to_content_menu",
                on_click=self.generate_publication_service.handle_go_to_content_menu,
            ),

            state=model.GeneratePublicationStates.text_too_long_alert,
            getter=self.generate_publication_getter.get_text_too_long_alert_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_combine_images_choice_window(self) -> Window:
        return Window(
            Multi(
                Const("📐 <b>Объединение изображений</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Const("🖼️ <i>У вас уже есть изображение в публикации</i><br><br>"),
                            Const("💡 <b>Выберите действие:</b>"),
                        ),
                        False: Multi(
                            Const("📤 <i>Загрузите от 2 до 3 изображений для объединения</i>"),
                        ),
                    },
                    selector="has_current_image"
                ),
                sep="",
            ),

            Column(
                Button(
                    Const("➕ Объединить с текущим"),
                    id="combine_with_current",
                    on_click=self.generate_publication_service.handle_combine_with_current,
                    when="has_current_image",
                ),
                Button(
                    Const("🔄 Начать с новых"),
                    id="combine_from_scratch",
                    on_click=self.generate_publication_service.handle_combine_from_scratch,
                    when="has_current_image",
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_image_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu, ShowMode.EDIT),
            ),

            state=model.GeneratePublicationStates.combine_images_choice,
            getter=self.generate_publication_getter.get_combine_images_choice_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_combine_images_upload_window(self) -> Window:
        return Window(
            Multi(
                Const("📤 <b>Загрузка изображений</b><br><br>"),
                Case(
                    {
                        True: Format("🖼️ <b>Изображений загружено: {combine_images_count} из 3</b><br>"),
                        False: Const(""),
                    },
                    selector="has_combine_images"
                ),
                Case(
                    {
                        True: Format("<br>📍 <b>Сейчас показано:</b> изображение {combine_current_index} из {combine_images_count}"),
                        False: Const(""),
                    },
                    selector="has_multiple_combine_images"
                ),
                Const("<br><br>📷 <i>Отправьте изображения (максимум 3)</i><br>"),
                Const("💡 <i>После загрузки всех изображений нажмите \"Далее\"</i>"),
                # Error messages
                Case(
                    {
                        True: Const(
                            "<br><br>❌ <b>Неверный формат файла</b><br><i>Отправьте изображение (не другой тип файла)</i>"),
                        False: Const(""),
                    },
                    selector="has_invalid_combine_image_type"
                ),
                Case(
                    {
                        True: Const("<br><br>📁 <b>Файл слишком большой</b><br><i>Максимум 10 МБ</i>"),
                        False: Const(""),
                    },
                    selector="has_big_combine_image_size"
                ),
                Case(
                    {
                        True: Const("<br><br>⚠️ <b>Достигнут лимит</b><br><i>Максимум 3 изображения</i>"),
                        False: Const(""),
                    },
                    selector="combine_images_limit_reached"
                ),
                Case(
                    {
                        True: Const("<br><br>⚠️ <b>Минимум 2 изображения</b><br><i>Загрузите хотя бы 2 изображения</i>"),
                        False: Const(""),
                    },
                    selector="not_enough_combine_images"
                ),
                sep="",
            ),

            DynamicMedia(
                selector="combine_current_image_media",
                when="has_combine_images",
            ),

            Row(
                Button(
                    Const("⬅️ Предыдущая"),
                    id="prev_combine_image",
                    on_click=self.generate_publication_service.handle_prev_combine_image,
                    when="has_multiple_combine_images",
                ),
                Button(
                    Const("➡️ Следующая"),
                    id="next_combine_image",
                    on_click=self.generate_publication_service.handle_next_combine_image,
                    when="has_multiple_combine_images",
                ),
                when="has_multiple_combine_images",
            ),

            MessageInput(
                func=self.generate_publication_service.handle_combine_image_upload,
            ),

            Column(
                Button(
                    Const("🗑️ Удалить текущее"),
                    id="delete_combine_image",
                    on_click=self.generate_publication_service.handle_delete_combine_image,
                    when="has_combine_images",
                ),
                Button(
                    Const("▶️ Далее"),
                    id="next_to_prompt",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.combine_images_prompt, ShowMode.EDIT),
                    when="has_enough_combine_images",
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_image_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu, ShowMode.EDIT),
            ),

            state=model.GeneratePublicationStates.combine_images_upload,
            getter=self.generate_publication_getter.get_combine_images_upload_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_combine_images_prompt_window(self) -> Window:
        return Window(
            Multi(
                Case(
                    {
                        False: Multi(
                            Const("✍️ <b>Как объединить изображения?</b><br><br>"),
                            Const("💬 <b>Опишите, как расположить изображения:</b><br>"),
                            Const("• <i>Расположите горизонтально</i><br>"),
                            Const("• <i>В виде коллажа</i><br>"),
                            Const("• <i>Наложите друг на друга</i><br>"),
                            Const("• <i>Вертикально, одно под другим</i><br><br>"),
                            Const("🎤 <i>Можно отправить текст или голосовое сообщение</i><br>"),
                            Const("⏭️ <i>Или пропустите этот шаг — ИИ сам решит, как лучше</i>"),
                        ),
                        True: Multi(
                            Const("⏳ <b>Объединяю изображения...</b><br>"),
                            Const("🕐 <i>Это может занять время. Пожалуйста, подождите.</i>"),
                        ),
                    },
                    selector="is_combining_images"
                ),
                Case(
                    {
                        True: Const("<br><br>🔄 <b>Распознаю голосовое сообщение...</b>"),
                        False: Const(""),
                    },
                    selector="voice_transcribe"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком короткое описание</b><br><i>Минимум 10 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_small_combine_prompt"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком длинное описание</b><br><i>Максимум 1000 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_big_combine_prompt"
                ),
                Case(
                    {
                        True: Const("<br><br>🎤 <b>Неверный формат</b><br><i>Отправьте текст, голосовое сообщение или аудиофайл</i>"),
                        False: Const(""),
                    },
                    selector="has_invalid_content_type"
                ),
                sep="",
            ),

            MessageInput(
                func=self.generate_publication_service.handle_combine_prompt_input,
            ),

            Column(
                Button(
                    Const("🔗 Объединить"),
                    id="execute_combine",
                    on_click=self.generate_publication_service.handle_execute_combine,
                    when=~F["is_combining_images"]
                ),
                Button(
                    Const("⏭️ Пропустить"),
                    id="skip_prompt",
                    on_click=self.generate_publication_service.handle_execute_combine,
                    when=~F["is_combining_images"]
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_upload",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.combine_images_upload, ShowMode.EDIT),
                when=~F["is_combining_images"]
            ),

            state=model.GeneratePublicationStates.combine_images_prompt,
            getter=self.generate_publication_getter.get_combine_images_prompt_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_combine_images_confirm_window(self) -> Window:
        return Window(
            Multi(
                Const("✅ <b>Результат объединения</b><br><br>"),
                Const("🖼️ <b>Объединенное изображение:</b>"),
                sep="",
            ),

            DynamicMedia(
                selector="combine_result_media",
            ),

            Multi(
                Case(
                    {
                        True: Multi(
                            Const("<br><br>📷 <b>Предыдущее изображение:</b>"),
                        ),
                        False: Const(""),
                    },
                    selector="has_old_image_backup"
                ),
                sep="",
            ),

            DynamicMedia(
                selector="old_image_backup_media",
                when="has_old_image_backup",
            ),

            Multi(
                Const("<br><br>💡 <b>Использовать объединенное изображение?</b>"),
                sep="",
            ),

            Row(
                Button(
                    Const("✅ Использовать"),
                    id="confirm_combine",
                    on_click=self.generate_publication_service.handle_confirm_combine,
                ),
                Button(
                    Const("❌ Отменить"),
                    id="cancel_combine",
                    on_click=self.generate_publication_service.handle_cancel_combine,
                ),
            ),

            state=model.GeneratePublicationStates.combine_images_confirm,
            getter=self.generate_publication_getter.get_combine_images_confirm_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_publication_success_window(self) -> Window:
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
                Const("📋 К меню контента"),
                id="go_to_content_menu",
                on_click=self.generate_publication_service.handle_go_to_content_menu,
            ),

            state=model.GeneratePublicationStates.publication_success,
            getter=self.generate_publication_getter.get_publication_success_data,
            parse_mode=SULGUK_PARSE_MODE,
        )