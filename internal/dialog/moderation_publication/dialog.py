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
            self.get_social_network_select_window(),
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

            TextInput(
                id="regenerate_prompt_input",
                on_success=self.moderation_publication_service.handle_regenerate_text_with_prompt,
            ),

            Button(
                Const("◀️ Назад"),
                id="preview",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_preview, ShowMode.EDIT),
                when=~F["is_regenerating_text"]
            ),

            state=model.ModerationPublicationStates.edit_text_menu,
            getter=self.moderation_publication_getter.get_edit_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_text_window(self) -> Window:
        return Window(
            Multi(
                Const("✍️ <b>Редактирование текста</b><br><br>"),
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
                on_success=self.moderation_publication_service.handle_edit_text,
            ),

            Button(
                Const("◀️ Назад"),
                id="edit_text_menu",
                on_click=lambda c, b, d: d.switch_to(model.ModerationPublicationStates.edit_text_menu, ShowMode.EDIT),
            ),

            state=model.ModerationPublicationStates.edit_text,
            getter=self.moderation_publication_getter.get_edit_text_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_image_menu_window(self) -> Window:
        return Window(
            Case(
                {
                    False: Multi(
                        Const("🎨 <b>Настройка изображения</b><br><br>"),
                        Case(
                            {
                                True: Const(
                                    "✏️ <i>Опишите, как изменить картинку. Я внесу ваши правки в текущее изображение</i><br><br>"),
                                False: Const("🖼️ <i>Опишите, какую картинку создать</i><br><br>"),
                            },
                            selector="has_image"
                        ),
                        Const("📋 <b>Что указать в описании:</b><br>"),
                        Const("• 👥 <b>Объекты и персонажи</b> — кто или что на картинке<br>"),
                        Const("• 🎭 <b>Стиль и настроение</b> — реалистично, мультяшно, минимализм<br>"),
                        Const("• 🌍 <b>Фон и окружение</b> — улица, природа, офис и т.д.<br>"),
                        Const("• ✨ <b>Детали</b> — освещение, поза, аксессуары"),
                    ),
                    True: Multi(
                        Const("🪄 <b>Создаю изображение...</b><br><br>"),
                        Const("⏳ <i>Это займет около минуты</i>"),
                    ),
                },
                selector="is_generating_image"
            ),
            Case(
                {
                    True: Const("<br><br>❌ <b>Ошибка:</b> Описание изображения не может быть пустым"),
                    False: Const(""),
                },
                selector="has_void_image_prompt"
            ),
            Case(
                {
                    True: Const("<br><br>📏 <b>Слишком короткое описание</b><br>💡 <i>Минимум 5 символов</i>"),
                    False: Const(""),
                },
                selector="has_small_image_prompt"
            ),
            Case(
                {
                    True: Const("<br><br>📏 <b>Слишком длинное описание</b><br>⚠️ <i>Максимум 500 символов</i>"),
                    False: Const(""),
                },
                selector="has_big_image_prompt"
            ),

            DynamicMedia(
                selector="preview_image_media",
                when="has_image",
            ),

            Column(
                Button(
                    Const("🎨 Сгенерировать картинку"),
                    id="generate_image",
                    on_click=self.moderation_publication_service.handle_generate_new_image,
                ),
                Button(
                    Const("📷 Загрузить своё фото"),
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