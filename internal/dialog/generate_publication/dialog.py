from aiogram_dialog import Window, Dialog, ShowMode
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
            self.get_image_menu_window(),
            self.get_upload_image_window(),
            self.get_social_network_select_window()
        )

    def get_select_category_window(self) -> Window:
        return Window(
            Multi(
                Const("📌 <b>Выберите рубрику, чтобы начать генерацию:</b>\n"),
                Case(
                    {
                        True: Const("<b>Актуальные рубрики</b>:"),
                        False: Multi(
                            Const("⚠️ <b>В организации нет созданных рубрик</b>"),
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
                Const("Назад"),
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
                Const("📝 Отправь мне текст или голосовое сообщение — я превращу его в контент."),
                Case(
                    {
                        True: Format("Ваш введенный текст: {input_text}"),
                        False: Const(""),
                    },
                    selector="has_input_text"
                ),
                # Text input error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст не может быть пустым"),
                        False: Const(""),
                    },
                    selector="has_void_input_text"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст слишком короткий (минимум 10 символов)"),
                        False: Const(""),
                    },
                    selector="has_small_input_text"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст слишком длинный (максимум 2000 символов)"),
                        False: Const(""),
                    },
                    selector="has_big_input_text"
                ),
                # Voice input error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Отправьте голосовое сообщение или аудиофайл"),
                        False: Const(""),
                    },
                    selector="has_invalid_voice_type"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Голосовое сообщение слишком длинное (максимум 5 минут)"),
                        False: Const(""),
                    },
                    selector="has_long_voice_duration"
                ),
                Case(
                    {
                        True: Const(
                            "⚠️ <b>Ошибка:</b> Не удалось распознать речь. Попробуйте записать заново или введите текст"),
                        False: Const(""),
                    },
                    selector="has_empty_voice_text"
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
                    Const("Далее"),
                    when="has_input_text"
                ),
                Back(Const("Назад")),
            ),

            state=model.GeneratePublicationStates.input_text,
            getter=self.generate_publication_getter.get_input_text_data,
            parse_mode="HTML",
        )

    def get_generation_window(self) -> Window:
        return Window(
            Multi(
                Const("Добавим картинку?"),
                sep="",
            ),

            Column(
                Button(
                    Const("Только текст"),
                    id="text_only",
                    on_click=self.generate_publication_service.handle_generate_text,
                ),
                Button(
                    Const("С картинкой"),
                    id="with_image",
                    on_click=self.generate_publication_service.handle_generate_text_with_image,
                ),
            ),

            Back(Const("Назад")),

            state=model.GeneratePublicationStates.generation,
            getter=self.generate_publication_getter.get_input_text_data,
            parse_mode="HTML",
        )

    def get_preview_window(self) -> Window:
        return Window(
            Multi(
                Format("{publication_text}\n"),
                Case(
                    {
                        True: Format("🖼 Изображение {current_image_index} из {total_images}"),
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
                        Const("Текст"),
                        id="edit_text_menu",
                        on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu,
                                                             ShowMode.EDIT),
                    ),
                    Button(
                        Const("Картинка"),
                        id="edit_image_menu",
                        on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu, ShowMode.EDIT),
                    ),
                ),
                Button(
                    Const("Место публикации"),
                    id="select_social_network",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.social_network_select,
                                                         ShowMode.EDIT),
                    when="can_publish_directly",
                ),
                Button(
                    Const("Добавить в черновики черновики"),
                    id="save_draft",
                    on_click=self.generate_publication_service.handle_add_to_drafts,
                ),
                Button(
                    Const("Отправить на модерацию"),
                    id="send_moderation",
                    on_click=self.generate_publication_service.handle_send_to_moderation,
                    when="requires_moderation",
                ),
                Button(
                    Const("Опубликовать"),
                    id="publish_now",
                    on_click=self.generate_publication_service.handle_publish_now,
                    when="can_publish_directly",
                ),
            ),
            Button(
                Const("Отмена"),
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
                Case(
                    {
                        False: Multi(
                            Const("✏️ <b>Редактирование текста</b>"),
                            Const("📌 Напишите, что нужно изменить в тексте -- и отредактирую его!"),
                        ),
                        True: Multi(
                            Format("📌 <b>Ваши указания:</b>\n<i>{regenerate_prompt}</i>\n\n"),
                            Const("⏳ <b>Перегенерирую текст...</b>\n"),
                            Const("Это может занять время. Пожалуйста, ожидайте."),
                        ),
                    },
                    selector="is_regenerating_text"
                ),
                sep="",
            ),

            Column(
                Button(
                    Const("Перегенерировать текст"),
                    id="regenerate_all",
                    on_click=self.generate_publication_service.handle_regenerate_text,
                ),
                Button(
                    Const("Написать свой текст"),
                    id="edit_content",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text, ShowMode.EDIT),
                ),
            ),
            Button(
                Const("Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview, ShowMode.EDIT),
            ),

            TextInput(
                id="regenerate_prompt_input",
                on_success=self.generate_publication_service.handle_regenerate_text_with_prompt,
            ),

            state=model.GeneratePublicationStates.edit_text_menu,
            parse_mode="HTML",
        )

    def get_edit_text_window(self) -> Window:
        return Window(
            Multi(
                Const("✍️ <b>Напишите итоговый текст"),
                # Add error messages
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст не может быть пустым"),
                        False: Const(""),
                    },
                    selector="has_void_text"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст слишком короткий (минимум 50 символов)"),
                        False: Const(""),
                    },
                    selector="has_small_text"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Текст слишком длинный (максимум 4000 символов)"),
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
                Const("Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.edit_text_menu, ShowMode.EDIT),
            ),

            state=model.GeneratePublicationStates.edit_text,
            getter=self.generate_publication_getter.get_edit_text_data,
            parse_mode="HTML",
        )

    def get_image_menu_window(self) -> Window:
        return Window(
            Case(
                {
                    False: Multi(
                        Case(
                            {
                                True: Multi(
                                    Const("Опиши, как изменить картинку. Я внесу твои правки в текущую фотографию.")

                                ),
                                False: Const("Опиши, какую картинку мне создать."),
                            },
                            selector="has_image"
                        ),
                        Const("Объекты и персонажи (кто или что на картинке)"),
                        Const("Стиль и настроение (реалистично, мультяшно, минимализм, тёплые или холодные цвета)"),
                        Const("Фон или окружение (улица, природа, офис и т.д.)"),
                        Const("Дополнительные детали (например, освещение, поза, аксессуары)"),
                    ),
                    True: Multi(
                        Format("🪄 Сейчас всё сделаю! Одну минуту."),
                    ),
                },
                selector="is_generating_image"
            ),
            Case(
                {
                    True: Const("⚠️ <b>Ошибка:</b> Описание изображения не может быть пустым"),
                    False: Const(""),
                },
                selector="has_void_image_prompt"
            ),
            Case(
                {
                    True: Const("⚠️ <b>Ошибка:</b> Описание слишком короткое (минимум 5 символов)"),
                    False: Const(""),
                },
                selector="has_small_image_prompt"
            ),
            Case(
                {
                    True: Const(
                        "⚠️ <b>Ошибка:</b> Описание слишком длинное (максимум 500 символов)"),
                    False: Const(""),
                },
                selector="has_big_image_prompt"
            ),
            Column(
                Button(
                    Const("Сгенерировать картинку"),
                    id="generate_image",
                    on_click=self.generate_publication_service.handle_generate_new_image,
                ),
                Button(
                    Const("Использовать мое фото"),
                    id="upload_image",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.upload_image, ShowMode.EDIT),
                ),
                Button(
                    Const("Удалить"),
                    id="remove_image",
                    on_click=self.generate_publication_service.handle_remove_image,
                    when="has_image",
                ),
            ),

            TextInput(
                id="image_prompt_input",
                on_success=self.generate_publication_service.handle_generate_image_with_prompt,
            ),
            Button(
                Const("Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview, ShowMode.EDIT),
            ),

            state=model.GeneratePublicationStates.image_menu,
            getter=self.generate_publication_getter.get_image_menu_data,
            parse_mode="HTML",
        )

    def get_upload_image_window(self) -> Window:
        return Window(
            Multi(
                Const("Отправьте свое фото"),
                # Add error messages
                Case(
                    {
                        True: Const(
                            "⚠️ <b>Ошибка:</b> Пожалуйста, отправьте изображение (не другой тип файла)"),
                        False: Const(""),
                    },
                    selector="has_invalid_image_type"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Файл слишком большой (максимум 10 МБ)"),
                        False: Const(""),
                    },
                    selector="has_big_image_size"
                ),
                Case(
                    {
                        True: Const("⚠️ <b>Ошибка:</b> Не удалось обработать изображение, попробуйте другое"),
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
                Const("📄 ◀️ Назад"),
                id="image_menu",
                on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.image_menu, ShowMode.EDIT),
            ),

            state=model.GeneratePublicationStates.upload_image,
            getter=self.generate_publication_getter.get_upload_image_data,
            parse_mode="HTML",
        )

    def get_social_network_select_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Выбор социальных сетей</b>\n"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Нет подключенных социальных сетей!</b>\n\n"),
                            Const(
                                "🔗 <i>Для публикации постов необходимо подключить хотя бы одну социальную сеть в настройках организации.</i>\n\n"),
                            Const("Обратитесь к администратору для подключения социальных сетей."),
                        ),
                        False: Const("✅ <b>Выберите, где опубликовать:</b>"),
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
                    Const("Назад"),
                    id="back_to_preview",
                    on_click=lambda c, b, d: d.switch_to(model.GeneratePublicationStates.preview, ShowMode.EDIT),
                ),
            ),

            state=model.GeneratePublicationStates.social_network_select,
            getter=self.generate_publication_getter.get_social_network_select_data,
            parse_mode="HTML",
        )
