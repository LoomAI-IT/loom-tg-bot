from aiogram import F
from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Checkbox
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia
from sulguk import SULGUK_PARSE_MODE

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
            self.get_new_image_confirm_window(),
            self.get_combine_images_choice_window(),
            self.get_combine_images_upload_window(),
            self.get_combine_images_prompt_window(),
            self.get_social_network_select_window(),
            self.get_text_too_long_alert_window(),
            self.get_publication_success_window()
        )

    def get_moderation_list_window(self) -> Window:
        return Window(
            Multi(
                Const("🔍 <b>Модерация публикаций</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Format("{publication_text}<br><br>"),
                            Format("👤 <b>Автор:</b> {creator_name}<br>"),
                            Format("🏷️ <b>Рубрика:</b> {category_name}<br>"),
                            Format("📅 <b>Создано:</b> <code>{created_at}</code><br>"),
                        ),
                        False: Multi(
                            Const("✅ <b>Нет публикаций на модерации</b><br><br>"),
                            Const("💫 <i>Все публикации обработаны или еще не поступали</i>"),
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
                    on_click=self.moderation_publication_service.handle_navigate_publication,
                    when="has_prev",
                ),
                Button(
                    Format("📊 {current_index}/{total_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer("📈 Навигация по публикациям"),
                    when="has_publications",
                ),
                Button(
                    Const("➡️ След"),
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
                        Const("🌐 Выбрать платформы"),
                        id="select_social_network",
                        on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.social_network_select,
                                                             ShowMode.EDIT),
                    ),
                ),
                Row(
                    Button(
                        Const("✅ Одобрить"),
                        id="approve",
                        on_click=self.moderation_publication_service.handle_publish_now,
                    ),
                    Button(
                        Const("❌ Отклонить"),
                        id="reject_with_comment",
                        on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.reject_comment),
                    ),
                ),
                when="has_publications",
            ),

            Row(
                Button(
                    Const("◀️ Меню контента"),
                    id="back_to_content_menu",
                    on_click=self.moderation_publication_service.handle_back_to_content_menu,
                ),
            ),

            state=model.ModerationPublicationStates.moderation_list,
            getter=self.moderation_publication_getter.get_moderation_list_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_reject_comment_window(self) -> Window:
        return Window(
            Multi(
                Const("❌ <b>Отклонение публикации</b><br><br>"),
                Format("👤 <b>Автор:</b> {creator_name}<br><br>"),
                Const("💬 <b>Укажите причину отклонения:</b><br>"),
                Const("💌 <i>Автор получит уведомление с вашим комментарием</i><br><br>"),
                Case(
                    {
                        True: Multi(
                            Const("📄 <b>Ваш комментарий:</b><br>"),
                            Format("💭 <i>«{reject_comment}»</i>"),
                        ),
                        False: Const("⌨️ <i>Ожидание ввода комментария...</i>"),
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
                    Const("◀️ Назад"),
                    id="back_to_moderation_list",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.moderation_list),
                ),
            ),

            state=model.ModerationPublicationStates.reject_comment,
            getter=self.moderation_publication_getter.get_reject_comment_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_preview_window(self) -> Window:
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

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            Row(
                Button(
                    Const("⬅️ Пред изображение"),
                    id="prev_image",
                    on_click=self.moderation_publication_service.handle_prev_image,
                    when="has_multiple_images",
                ),
                Button(
                    Const("➡️ След изображение"),
                    id="next_image",
                    on_click=self.moderation_publication_service.handle_next_image,
                    when="has_multiple_images",
                ),
                when="has_multiple_images",
            ),

            Column(
                Button(
                    Const("📝 Изменить текст"),
                    id="edit_text_menu",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_text_menu),
                ),
                Button(
                    Const("🖼️ Изменить изображение"),
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
                    Const("◀️ Назад к списку"),
                    id="back_to_moderation_list",
                    on_click=self.moderation_publication_service.handle_back_to_moderation_list,
                ),
            ),

            state=model.ModerationPublicationStates.edit_preview,
            getter=self.moderation_publication_getter.get_edit_preview_data,
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
                func=self.moderation_publication_service.handle_regenerate_text_prompt_input,
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

            state=model.ModerationPublicationStates.edit_text_menu,
            getter=self.moderation_publication_getter.get_edit_publication_text_data,
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
                on_success=self.moderation_publication_service.handle_edit_text,
            ),

            Button(
                Const("◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_text_menu, ShowMode.EDIT),
            ),

            state=model.ModerationPublicationStates.edit_text,
            getter=self.moderation_publication_getter.get_edit_publication_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_image_menu_window(self) -> Window:
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
                func=self.moderation_publication_service.handle_generate_image_prompt_input,
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
                    Const("📐 Объединить изображения"),
                    id="combine_images",
                    on_click=self.moderation_publication_service.handle_combine_images_start,
                ),
                Button(
                    Const("🗑️ Удалить изображение"),
                    id="remove_image",
                    on_click=self.moderation_publication_service.handle_remove_image,
                    when="has_image",
                ),
                when=~F["is_generating_image"]
            ),

            Button(
                Const("◀️ Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview, ShowMode.EDIT),
                when=~F["is_generating_image"]
            ),

            state=model.ModerationPublicationStates.edit_image_menu,
            getter=self.moderation_publication_getter.get_image_menu_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_upload_image_window(self) -> Window:
        return Window(
            Multi(
                Const("📷 <b>Загрузка изображения</b><br><br>"),
                Const("📤 <i>Отправьте своё изображение</i><br><br>"),
                Const("📋 <b>Поддерживаемые форматы:</b> JPG, PNG, GIF<br>"),
                Const("📏 <b>Максимальный размер:</b> 10 МБ"),
                Case(
                    {
                        True: Const(
                            "<br><br>❌ <b>Неверный формат файла</b><br>⚠️ <i>Отправьте изображение (не другой тип файла)</i>"),
                        False: Const(""),
                    },
                    selector="has_invalid_image_type"
                ),
                Case(
                    {
                        True: Const("<br><br>📁 <b>Файл слишком большой</b><br>⚠️ <i>Максимум 10 МБ</i>"),
                        False: Const(""),
                    },
                    selector="has_big_image_size"
                ),
                Case(
                    {
                        True: Const(
                            "<br><br>💥 <b>Ошибка обработки</b><br>🔄 <i>Не удалось обработать изображение, попробуйте другое</i>"),
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
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_social_network_select_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Выбор платформ для публикации</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Социальные сети не подключены!</b><br><br>"),
                            Const(
                                "🔗 <i>Для публикации необходимо подключить хотя бы одну социальную сеть в настройках организации</i><br><br>"),
                            Const("👨‍💼 <b>Обратитесь к администратору для настройки подключений</b>"),
                        ),
                        False: Multi(
                            Const("📱 <b>Выберите платформы для публикации:</b><br><br>"),
                            Const("💡 <i>Можно выбрать несколько вариантов одновременно</i>"),
                        ),
                    },
                    selector="no_connected_networks"
                ),
                sep="",
            ),

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

            Row(
                Button(
                    Const("◀️ Назад к списку"),
                    id="back_to_preview",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.moderation_list,
                                                         ShowMode.EDIT),
                ),
            ),

            state=model.ModerationPublicationStates.social_network_select,
            getter=self.moderation_publication_getter.get_social_network_select_data,
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
                    on_click=self.moderation_publication_service.handle_compress_text,
                ),
                Button(
                    Const("🗑️ Отказаться от фото"),
                    id="remove_photo",
                    on_click=self.moderation_publication_service.handle_remove_photo_from_long_text,
                ),
                Button(
                    Const("↩️ Вернуть предыдущий текст"),
                    id="restore_previous",
                    on_click=self.moderation_publication_service.handle_restore_previous_text,
                    when="has_previous_text",
                ),
            ),

            state=model.ModerationPublicationStates.text_too_long_alert,
            getter=self.moderation_publication_getter.get_text_too_long_alert_data,
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
                Const("📋 К списку публикаций на модерации"),
                id="go_to_content_menu",
                on_click=self.moderation_publication_service.handle_back_to_moderation_list,
            ),

            state=model.ModerationPublicationStates.publication_success,
            getter=self.moderation_publication_getter.get_publication_success_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_new_image_confirm_window(self) -> Window:
        return Window(
            Multi(
                Case(
                    {
                        False: Multi(
                            Const("🖼️ <b>Результат генерации</b><br><br>"),
                            Case(
                                {
                                    True: Multi(
                                        Case(
                                            {
                                                True: Const("📍 <b>Показано:</b> старая картинка<br><br>"),
                                                False: Const("📍 <b>Показано:</b> новая картинка<br><br>"),
                                            },
                                            selector="showing_old_image"
                                        ),
                                    ),
                                    False: Const(""),
                                },
                                selector="has_old_image"
                            ),
                            Const("💡 <b>Что хотите сделать?</b><br>"),
                            Const("• Принять изображение как есть<br>"),
                            Const("• Написать или записать правки для улучшения<br><br>"),
                            Const("💬 <i>Отправьте текст или голосовое сообщение с правками, и изображение будет отредактировано</i>"),
                        ),
                        True: Multi(
                            Const("⏳ <b>Применяю правки к изображению...</b><br>"),
                            Const("🕐 <i>Это может занять время. Пожалуйста, подождите.</i>"),
                        ),
                    },
                    selector="is_applying_edits"
                ),
                Case(
                    {
                        True: Format("<br><br>📝 <b>Ваши правки:</b><br><i>{edit_image_prompt}</i>"),
                        False: Const(""),
                    },
                    selector="has_image_edit_prompt"
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
                        True: Const("<br><br>📏 <b>Слишком короткое описание правок</b><br><i>Минимум 10 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_small_edit_prompt"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком длинное описание правок</b><br><i>Максимум 1000 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_big_edit_prompt"
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

            DynamicMedia(
                selector="new_image_media",
            ),

            Row(
                Button(
                    Const("⬅️ Старая"),
                    id="show_old_image",
                    on_click=self.moderation_publication_service.handle_show_old_image,
                    when=F["has_old_image"] & F["showing_new_image"] & ~F["is_applying_edits"]
                ),
                Button(
                    Const("➡️ Новая"),
                    id="show_new_image",
                    on_click=self.moderation_publication_service.handle_show_new_image,
                    when=F["has_old_image"] & F["showing_old_image"] & ~F["is_applying_edits"]
                ),
                when="has_old_image",
            ),

            MessageInput(
                func=self.moderation_publication_service.handle_edit_image_prompt_input_from_confirm_new_image,
            ),

            Column(
                Button(
                    Const("📐 Объединить с другими фото"),
                    id="combine_from_new_image",
                    on_click=self.moderation_publication_service.handle_combine_image_from_new_image,
                    when=~F["is_applying_edits"]
                ),
                Row(
                    Button(
                        Const("✅ Принять"),
                        id="confirm_new_image",
                        on_click=self.moderation_publication_service.handle_confirm_new_image,
                        when=~F["is_applying_edits"]
                    ),
                    Button(
                        Const("❌ Отклонить"),
                        id="reject_new_image",
                        on_click=self.moderation_publication_service.handle_reject_new_image,
                        when=~F["is_applying_edits"]
                    ),
                ),
            ),

            state=model.ModerationPublicationStates.new_image_confirm,
            getter=self.moderation_publication_getter.get_new_image_confirm_data,
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
                    selector="has_image"
                ),
                sep="",
            ),

            Column(
                Button(
                    Const("➕ Объединить с текущим"),
                    id="combine_with_current",
                    on_click=self.moderation_publication_service.handle_combine_with_current_image,
                    when="has_image",
                ),
                Button(
                    Const("🔄 Начать с новых"),
                    id="combine_from_scratch",
                    on_click=self.moderation_publication_service.handle_combine_image_from_scratch,
                    when="has_image",
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_image_menu",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_image_menu, ShowMode.EDIT),
            ),

            state=model.ModerationPublicationStates.combine_images_choice,
            getter=self.moderation_publication_getter.get_combine_images_choice_data,
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
                Const("📷 <i>Отправьте изображения (максимум 3)</i><br>"),
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
                    on_click=self.moderation_publication_service.handle_prev_combine_image,
                    when="has_multiple_combine_images",
                ),
                Button(
                    Const("➡️ Следующая"),
                    id="next_combine_image",
                    on_click=self.moderation_publication_service.handle_next_combine_image,
                    when="has_multiple_combine_images",
                ),
                when="has_multiple_combine_images",
            ),

            MessageInput(
                func=self.moderation_publication_service.handle_combine_image_upload,
            ),

            Column(
                Button(
                    Const("🗑️ Удалить текущее"),
                    id="delete_combine_image",
                    on_click=self.moderation_publication_service.handle_delete_combine_image,
                    when="has_combine_images",
                ),
                Button(
                    Const("▶️ Далее"),
                    id="next_to_prompt",
                    on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.combine_images_prompt, ShowMode.EDIT),
                    when="has_enough_combine_images",
                ),
            ),

            Button(
                Const("◀️ Назад"),
                id="back_from_combine_upload",
                on_click=self.moderation_publication_service.handle_back_from_combine_image_upload,
            ),

            state=model.ModerationPublicationStates.combine_images_upload,
            getter=self.moderation_publication_getter.get_combine_images_upload_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_combine_images_prompt_window(self) -> Window:
        return Window(
            Multi(
                Case(
                    {
                        False: Multi(
                            Const("✨ <b>Создание единого изображения из нескольких фото</b><br><br>"),
                            Format("🖼️ Изображение {combine_current_index} из {combine_images_count}<br><br>"),
                            Const("💬 <b>Опишите, как объединить загруженные фото в одно:</b><br><br>"),
                            Const("📸 <b>Что можно указать про конкретные фото:</b><br>"),
                            Const("• Что взять с первого/второго/третьего фото<br>"),
                            Const("• Какие элементы использовать (человек, фон, объекты)<br>"),
                            Const("• Что убрать или изменить на каждом фото<br><br>"),
                            Const("🎨 <b>Варианты расположения:</b><br>"),
                            Const("• Горизонтально (фото рядом слева направо)<br>"),
                            Const("• Вертикально (фото одно под другим)<br>"),
                            Const("• Коллаж (произвольное расположение)<br>"),
                            Const("• Наложение (одно фото поверх другого)<br><br>"),
                            Const("✏️ <b>Дополнительные пожелания:</b><br>"),
                            Const("• Добавить рамки, переходы между фото<br>"),
                            Const("• Изменить размеры отдельных элементов<br>"),
                            Const("• Настроить цвета, яркость, фильтры<br>"),
                            Const("• Любые другие идеи по композиции<br><br>"),
                            Const("🎤 <i>Отправьте текст или голосовое сообщение</i><br>"),
                            Const("⏭️ <i>Или пропустите — ИИ сам решит, как лучше объединить фото</i>"),
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
                    selector="has_small_combine_image_prompt"
                ),
                Case(
                    {
                        True: Const("<br><br>📏 <b>Слишком длинное описание</b><br><i>Максимум 1000 символов</i>"),
                        False: Const(""),
                    },
                    selector="has_big_combine_image_prompt"
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

            DynamicMedia(
                selector="combine_current_image_media",
                when="has_combine_images",
            ),

            Row(
                Button(
                    Const("⬅️ Предыдущая"),
                    id="prev_combine_image_prompt",
                    on_click=self.moderation_publication_service.handle_prev_combine_image,
                    when="has_multiple_combine_images",
                ),
                Button(
                    Const("➡️ Следующая"),
                    id="next_combine_image_prompt",
                    on_click=self.moderation_publication_service.handle_next_combine_image,
                    when="has_multiple_combine_images",
                ),
                when=~F["is_combining_images"],
            ),

            MessageInput(
                func=self.moderation_publication_service.handle_combine_image_prompt_input,
            ),

            Button(
                Const("⏭️ Пропустить"),
                id="skip_prompt",
                on_click=self.moderation_publication_service.handle_skip_combine_image_prompt,
                when=~F["is_combining_images"]
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_upload",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.combine_images_upload, ShowMode.EDIT),
                when=~F["is_combining_images"]
            ),

            state=model.ModerationPublicationStates.combine_images_prompt,
            getter=self.moderation_publication_getter.get_combine_images_prompt_data,
            parse_mode=SULGUK_PARSE_MODE,
        )