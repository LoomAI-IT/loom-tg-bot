from aiogram import F
from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Checkbox
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia

from internal import interface, model


class ModerationPublicationDialog(interface.IModerationPublicationDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            moderation_publication_service: interface.IModerationPublicationService,
            moderation_publication_getter: interface.IModerationPublicationGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.moderation_publication_service = moderation_publication_service
        self.moderation_publication_getter = moderation_publication_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_moderation_list_window(),
            self.get_reject_comment_window(),
            self.get_edit_preview_window(),
            self.get_edit_text_menu_window(),
            self.get_edit_text_window(),
            self.get_edit_image_menu_window(),
            self.get_upload_image_window(),
            self.get_social_network_select_window(),
        )

    def get_moderation_list_window(self) -> Window:
        return Window(
            Multi(
                Const("🔍 <b>Модерация публикаций</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Format("{publication_text}\n\n"),
                            Format("👤 Автор: <b>{creator_name}</b>\n"),
                            Format("🏷 Рубрика: <b>{category_name}</b>\n"),
                            Format("📅 Создано: {created_at}\n"),

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
                    on_click=lambda c, b, d: c.answer(),
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

            Column(
                Row(
                    Button(
                        Const("✏️ Редактировать"),
                        id="edit",
                        on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview),
                    ),
                    Button(
                        Const("🌐 Выбрать место публикации"),
                        id="select_social_network",
                        on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.social_network_select,
                                                             ShowMode.EDIT),
                    ),
                    Button(
                        Const("✅ Опубликовать"),
                        id="approve",
                        on_click=self.moderation_publication_service.handle_publish_now,
                    ),
                ),
                Row(
                    Button(
                        Const("💬 Отклонить"),
                        id="reject_with_comment",
                        on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.reject_comment),
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
            getter=self.moderation_publication_getter.get_moderation_list_data,
            parse_mode="HTML",
        )

    def get_reject_comment_window(self) -> Window:
        return Window(
            Multi(
                Const("❌ <b>Отклонение публикации</b>\n\n"),
                Format("📄 Публикация: <b>{publication_name}</b>\n"),
                Format("👤 Автор: <b>{creator_name}</b>\n\n"),
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
            getter=self.moderation_publication_getter.get_reject_comment_data,
            parse_mode="HTML",
        )

    def get_edit_preview_window(self) -> Window:
        return Window(
            Multi(
                Const("✏️ <b>Редактирование публикации</b>\n\n"),
                Format("{publication_text}\n\n"),
                Format("👤 Автор: <b>{creator_name}</b>\n"),
                Format("🏷 Рубрика: <b>{category_name}</b>\n"),
                Format("📅 Создано: {created_at}\n\n"),

                Case(
                    {
                        True: Format("\n\n🖼 Изображение {current_image_index} из {total_images}"),
                        False: Const(""),
                    },
                    selector="has_multiple_images"
                ),
                Case(
                    {
                        True: Const("\n\n<i>❗️ Есть несохраненные изменения</i>"),
                        False: Const(""),
                    },
                    selector="has_changes"
                ),
                Const("📌 <b>Выберите, что изменить:</b>"),
                sep="",
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),


            Row(
                Button(
                    Const("⬅️"),
                    id="prev_image",
                    on_click=self.moderation_publication_service.handle_prev_image,
                    when="has_multiple_images",
                ),
                Button(
                    Const("➡️"),
                    id="next_image",
                    on_click=self.moderation_publication_service.handle_next_image,
                    when="has_multiple_images",
                ),
                when="has_multiple_images",
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
            getter=self.moderation_publication_getter.get_edit_preview_data,
            parse_mode="HTML",
        )

    def get_edit_text_menu_window(self) -> Window:
        return Window(
            Multi(
                Case(
                    {
                        False: Multi(
                            Const("✏️ <b>Редактирование текста</b>\n"),
                            Const("💭 <i>Напишите, что нужно изменить в тексте — я отредактирую его!</i>"),
                        ),
                        True: Case(
                            {
                                True: Multi(
                                    Format("📝 <b>Ваши указания:</b>\n<code>{regenerate_prompt}</code>\n"),
                                    Const("⏳ <b>Перегенерирую текст...</b>\n"),
                                    Const("🕐 <i>Это может занять время. Пожалуйста, подождите.</i>"),
                                ),
                                False: Multi(
                                    Const("⏳ <b>Перегенерирую текст...</b>\n"),
                                    Const("🕐 <i>Это может занять время. Пожалуйста, подождите.</i>"),
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
                    on_click=self.moderation_publication_service.handle_regenerate_text,
                    when=~F["is_regenerating_text"]
                ),
                Button(
                    Const("✍️ Написать свой текст"),
                    id="edit_content",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_text, ShowMode.EDIT),
                    when=~F["is_regenerating_text"]
                ),
            ),
            Button(
                Const("◀️ Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview, ShowMode.EDIT),
                when=~F["is_regenerating_text"]
            ),

            TextInput(
                id="regenerate_prompt_input",
                on_success=self.moderation_publication_service.handle_regenerate_text_with_prompt,
            ),

            state=model.ModerationPublicationStates.edit_text_menu,
            getter=self.moderation_publication_getter.get_edit_text_data,
            parse_mode="HTML",
        )

    def get_edit_text_window(self) -> Window:
        return Window(
            Multi(
                Const("✍️ <b>Редактирование текста</b>\n"),
                Const("📝 <i>Напишите итоговый текст публикации</i>"),
                # Add error messages
                Case(
                    {
                        True: Const("\n❌ <b>Ошибка:</b> Текст не может быть пустым"),
                        False: Const(""),
                    },
                    selector="has_void_text"
                ),
                Case(
                    {
                        True: Const("\n📏 <b>Слишком короткий текст</b>\n<i>Минимум 50 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_small_text"
                ),
                Case(
                    {
                        True: Const("\n📏 <b>Слишком длинный текст</b>\n<i>Максимум 4000 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_big_text"
                ),
                sep="",
            ),

            TextInput(
                id="text_input",
                on_success=self.moderation_publication_service.handle_edit_text,
            ),

            Button(
                Const("◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_text_menu, ShowMode.EDIT),
            ),

            state=model.ModerationPublicationStates.edit_text,
            getter=self.moderation_publication_getter.get_edit_text_data,
            parse_mode="HTML",
        )

    def get_edit_image_menu_window(self) -> Window:
        return Window(
            Case(
                {
                    False: Multi(
                        Const("🎨 <b>Настройка изображения</b>\n"),
                        Case(
                            {
                                True: Multi(
                                    Const(
                                        "✏️ <i>Опишите, как изменить картинку. Я внесу ваши правки в текущее изображение.</i>\n\n")
                                ),
                                False: Const("🖼️ <i>Опишите, какую картинку создать.</i>\n\n"),
                            },
                            selector="has_image"
                        ),
                        Const("📋 <b>Что указать в описании:</b>\n"),
                        Const("• 👥 <b>Объекты и персонажи</b> — кто или что на картинке\n"),
                        Const("• 🎭 <b>Стиль и настроение</b> — реалистично, мультяшно, минимализм, цветовая гамма\n"),
                        Const("• 🌍 <b>Фон и окружение</b> — улица, природа, офис и т.д.\n"),
                        Const("• ✨ <b>Детали</b> — освещение, поза, аксессуары"),
                    ),
                    True: Multi(
                        Const("🪄 <b>Создаю изображение...</b>\n"),
                        Const("⏳ <i>Это займет около минуты</i>"),
                    ),
                },
                selector="is_generating_image"
            ),
            Case(
                {
                    True: Const("\n❌ <b>Ошибка:</b> Описание изображения не может быть пустым"),
                    False: Const(""),
                },
                selector="has_void_image_prompt"
            ),
            Case(
                {
                    True: Const("\n📏 <b>Слишком короткое описание</b>\n<i>Минимум 5 символов</i>"),
                    False: Const(""),
                },
                selector="has_small_image_prompt"
            ),
            Case(
                {
                    True: Const("\n📏 <b>Слишком длинное описание</b>\n<i>Максимум 500 символов</i>"),
                    False: Const(""),
                },
                selector="has_big_image_prompt"
            ),
            Column(
                Button(
                    Const("🎨 Сгенерировать картинку"),
                    id="generate_image",
                    on_click=self.moderation_publication_service.handle_generate_new_image,
                ),
                Button(
                    Const("📷 Использовать своё фото"),
                    id="upload_image",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.upload_image, ShowMode.EDIT),
                ),
                Button(
                    Const("🗑️ Удалить изображение"),
                    id="remove_image",
                    on_click=self.moderation_publication_service.handle_remove_image,
                    when="has_image",
                ),
                when=~F["is_generating_image"]
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            TextInput(
                id="image_prompt_input",
                on_success=self.moderation_publication_service.handle_generate_image_with_prompt,
            ),
            Button(
                Const("◀️ Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview, ShowMode.EDIT),
                when=~F["is_generating_image"]
            ),

            state=model.ModerationPublicationStates.edit_image_menu,
            getter=self.moderation_publication_getter.get_image_menu_data,
            parse_mode="HTML",
        )

    def get_upload_image_window(self) -> Window:
        return Window(
            Multi(
                Const("📷 <b>Загрузка изображения</b>\n"),
                Const("📤 <i>Отправьте своё изображение</i>"),
                # Add error messages
                Case(
                    {
                        True: Const(
                            "\n❌ <b>Неверный формат файла</b>\n<i>Отправьте изображение (не другой тип файла)</i>"),
                        False: Const(""),
                    },
                    selector="has_invalid_image_type"
                ),
                Case(
                    {
                        True: Const("\n📁 <b>Файл слишком большой</b>\n<i>Максимум 10 МБ</i>"),
                        False: Const(""),
                    },
                    selector="has_big_image_size"
                ),
                Case(
                    {
                        True: Const(
                            "\n⚠️ <b>Ошибка обработки</b>\n<i>Не удалось обработать изображение, попробуйте другое</i>"),
                        False: Const(""),
                    },
                    selector="has_image_processing_error"
                ),
                sep="",
            ),

            MessageInput(
                func=self.moderation_publication_service.handle_image_upload,
            ),

            Button(
                Const("◀️ Назад"),
                id="image_menu",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_image_menu, ShowMode.EDIT),
            ),

            state=model.ModerationPublicationStates.upload_image,
            getter=self.moderation_publication_getter.get_upload_image_data,
            parse_mode="HTML",
        )

    def get_social_network_select_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Выбор платформы для публикации</b>\n"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Социальные сети не подключены</b>\n"),
                            Const(
                                "🔗 <i>Для публикации необходимо подключить хотя бы одну социальную сеть в настройках организации</i>\n"),
                            Const("💡 <b>Обратитесь к администратору для настройки подключений</b>"),
                        ),
                        False: Multi(
                            Const("📱 <b>Выберите платформы для публикации:</b>\n"),
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
                    on_state_changed=self.moderation_publication_service.handle_toggle_social_network,
                    when="telegram_connected",
                ),
                Checkbox(
                    Const("✅ 🔵 ВКонтакте"),
                    Const("⬜ 🔵 ВКонтакте"),
                    id="vkontakte_checkbox",
                    default=False,
                    on_state_changed=self.moderation_publication_service.handle_toggle_social_network,
                    when="vkontakte_connected",
                ),
                when="has_available_networks",
            ),

            # Кнопки действий
            Row(
                Button(
                    Const("◀️ Назад"),
                    id="back_to_preview",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview, ShowMode.EDIT),
                ),
            ),

            state=model.ModerationPublicationStates.social_network_select,
            getter=self.moderation_publication_getter.get_social_network_select_data,
            parse_mode="HTML",
        )
