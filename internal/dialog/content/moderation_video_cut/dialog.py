from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Checkbox
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class VideoCutModerationDialog(interface.IVideoCutModerationDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            video_cut_moderation_service: interface.IVideoCutModerationService,
            video_cut_moderation_getter: interface.IVideoCutModerationGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.video_cut_moderation_service = video_cut_moderation_service
        self.video_cut_moderation_getter = video_cut_moderation_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_moderation_list_window(),
            self.get_reject_comment_window(),
            self.get_edit_preview_window(),
            self.get_edit_title_window(),
            self.get_edit_description_window(),
            self.get_edit_tags_window(),
            self.get_social_network_select_window(),
        )

    def get_moderation_list_window(self) -> Window:
        return Window(
            Multi(
                Const("🎬 <b>Модерация видео</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Format("📽️ <b>{video_name}</b><br>"),
                            Format("📝 {video_description}<br><br>"),
                            Case(
                                {
                                    True: Format("🏷️ <b>Теги:</b> <code>{video_tags}</code><br>"),
                                    False: Const("🏷️ <b>Теги:</b> <i>не указаны</i><br>"),
                                },
                                selector="has_tags"
                            ),
                            Format("👤 <b>Автор:</b> <code>{creator_name}</code><br>"),
                            Format("📅 <b>Создано:</b> <code>{created_at}</code><br>"),
                            Format("🔗 <b>Источник:</b> <a href='{youtube_reference}'>YouTube</a><br><br>"),
                        ),
                        False: Multi(
                            Const("📂 <b>Очередь модерации пуста</b><br><br>"),
                            Const("💡 <i>Все видео обработаны или ещё не поступали на проверку</i>"),
                        ),
                    },
                    selector="has_video_cuts"
                ),
                sep="",
            ),

            DynamicMedia(
                "video_media",
                when="has_video"
            ),

            Row(
                Button(
                    Const("⬅️ Пред"),
                    id="prev_video_cut",
                    on_click=self.video_cut_moderation_service.handle_navigate_video_cut,
                    when="has_prev",
                ),
                Button(
                    Format("📊 {current_index}/{total_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer("📈 Навигация по видео на модерации"),
                    when="has_video_cuts",
                ),
                Button(
                    Const("➡️ След"),
                    id="next_video_cut",
                    on_click=self.video_cut_moderation_service.handle_navigate_video_cut,
                    when="has_next",
                ),
                when="has_video_cuts",
            ),

            Column(
                Row(
                    Button(
                        Const("✏️ Редактировать"),
                        id="edit",
                        on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_preview),
                        when="has_video_cuts",
                    ),
                    Button(
                        Const("🌐 Выбрать соцсети"),
                        id="select_social_network",
                        on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.social_network_select,
                                                             ShowMode.EDIT),
                        when="has_video_cuts",
                    ),
                ),
                Button(
                    Const("✅ Одобрить и опубликовать"),
                    id="approve",
                    on_click=self.video_cut_moderation_service.handle_publish_now,
                    when="has_video_cuts",
                ),
                Button(
                    Const("❌ Отклонить с комментарием"),
                    id="reject_with_comment",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.reject_comment),
                    when="has_video_cuts",
                ),
                when="has_video_cuts",
            ),

            Row(
                Button(
                    Const("◀️ Меню контента"),
                    id="back_to_content_menu",
                    on_click=self.video_cut_moderation_service.handle_back_to_content_menu,
                ),
            ),

            state=model.VideoCutModerationStates.moderation_list,
            getter=self.video_cut_moderation_getter.get_moderation_list_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_reject_comment_window(self) -> Window:
        return Window(
            Multi(
                Const("❌ <b>Отклонение видео</b><br><br>"),
                Format("🎬 <b>Видео:</b> {video_name}<br>"),
                Format("👤 <b>Автор:</b> {creator_name}<br><br>"),
                Const("💬 <b>Укажите причину отклонения:</b><br>"),
                Const("📨 <i>Автор получит уведомление с вашим комментарием</i><br><br>"),
                Case(
                    {
                        True: Multi(
                            Const("📝 <b>Ваш комментарий:</b><br>"),
                            Format("<code>{reject_comment}</code>"),
                        ),
                        False: Const("⌨️ <i>Введите комментарий...</i>"),
                    },
                    selector="has_comment"
                ),
                sep="",
            ),
            Case(
                {
                    True: Const("<br><br>⚠️ <b>Комментарий не может быть пустым</b>"),
                    False: Const("")
                },
                selector="has_void_reject_comment"
            ),
            Case(
                {
                    True: Const("<br><br>📏 <b>Слишком короткий комментарий</b><br><i>Минимум 10 символов для информативности</i>"),
                    False: Const("")
                },
                selector="has_small_reject_comment"
            ),
            Case(
                {
                    True: Const("<br><br>📏 <b>Слишком длинный комментарий</b><br><i>Максимум 500 символов</i>"),
                    False: Const("")
                },
                selector="has_big_reject_comment"
            ),

            TextInput(
                id="reject_comment_input",
                on_success=self.video_cut_moderation_service.handle_reject_comment_input,
            ),

            Row(
                Button(
                    Const("📤 Отправить отклонение"),
                    id="send_rejection",
                    on_click=self.video_cut_moderation_service.handle_send_rejection,
                    when="has_comment",
                ),
                Button(
                    Const("◀️ Назад"),
                    id="back_to_moderation_list",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.moderation_list),
                ),
            ),

            state=model.VideoCutModerationStates.reject_comment,
            getter=self.video_cut_moderation_getter.get_reject_comment_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_preview_window(self) -> Window:
        return Window(
            Multi(
                Const("✏️ <b>Редактирование видео на модерации</b><br><br>"),
                Multi(
                    Format("📽️ <b>{video_name}</b><br>"),
                    Format("📝 {video_description}<br><br>"),
                    Case(
                        {
                            True: Format("🏷️ <b>Теги:</b> <code>{video_tags}</code><br>"),
                            False: Const("🏷️ <b>Теги:</b> <i>не указаны</i><br>"),
                        },
                        selector="has_tags"
                    ),
                    Format("👤 <b>Автор:</b> <code>{creator_name}</code><br>"),
                    Format("📅 <b>Создано:</b> <code>{created_at}</code><br>"),
                    Format("🔗 <b>Источник:</b> <a href='{youtube_reference}'>YouTube</a><br>"),
                ),
                Case(
                    {
                        True: Const("<br>⚠️ <b><i>Есть несохранённые изменения!</i></b><br>"),
                        False: Const(""),
                    },
                    selector="has_changes"
                ),
                Const("<br>📌 <b>Что требуется изменить?</b>"),
                sep="",
            ),

            DynamicMedia(
                "video_media",
                when="has_video"
            ),

            Column(
                Button(
                    Const("📝 Изменить название"),
                    id="edit_title",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_title),
                ),
                Button(
                    Const("📄 Изменить описание"),
                    id="edit_description",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_description),
                ),
                Button(
                    Const("🏷️ Изменить теги"),
                    id="edit_tags",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_tags),
                ),
            ),

            Row(
                Button(
                    Const("💾 Сохранить изменения"),
                    id="save_edits",
                    on_click=self.video_cut_moderation_service.handle_save_edits,
                    when="has_changes",
                ),
                Button(
                    Const("◀️ Назад"),
                    id="back_to_moderation_list",
                    on_click=self.video_cut_moderation_service.handle_back_to_moderation_list,
                ),
            ),

            state=model.VideoCutModerationStates.edit_preview,
            getter=self.video_cut_moderation_getter.get_edit_preview_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_title_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Изменение названия</b><br><br>"),
                Format("📋 <b>Текущее название:</b><br><i>{current_title}</i><br><br>"),
                Const("✍️ <b>Введите новое название:</b><br><br>"),
                Const("📏 <b>Ограничения по символам:</b><br>"),
                Const("🎬 YouTube Shorts: <code>максимум 100 символов</code><br>"),
                Const("📱 Instagram Reels: <code>максимум 2200 символов</code>"),
                sep="",
            ),
            Case(
                {
                    True: Const("<br><br>⚠️ <b>Название не может быть пустым</b>"),
                    False: Const("")
                },
                selector="has_void_title"
            ),
            Case(
                {
                    True: Const("<br><br>📏 <b>Слишком короткое название</b><br><i>Минимум 5 символов</i>"),
                    False: Const("")
                },
                selector="has_small_title"
            ),
            Case(
                {
                    True: Const("<br><br>📏 <b>Слишком длинное название</b><br><i>Максимум 100 символов для YouTube Shorts</i>"),
                    False: Const("")
                },
                selector="has_big_title"
            ),

            TextInput(
                id="title_input",
                on_success=self.video_cut_moderation_service.handle_edit_title,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_preview),
            ),

            state=model.VideoCutModerationStates.edit_title,
            getter=self.video_cut_moderation_getter.get_edit_title_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_description_window(self) -> Window:
        """Окно редактирования описания видео"""
        return Window(
            Multi(
                Const("📄 <b>Изменение описания</b><br><br>"),
                Format("📊 <b>Длина текущего описания:</b> <code>{current_description_length} символов</code><br><br>"),
                Const("<b>Ваше описание:</b><br>"),
                Format("{video_description}<br><br>"),
                Const("✍️ <b>Введите новое описание:</b><br><br>"),
                Const("📏 <b>Ограничения по символам:</b><br>"),
                Const("🎬 YouTube: <code>максимум 5000 символов</code><br>"),
                Const("📱 Instagram: <code>максимум 2200 символов</code><br><br>"),
                Const("💡 <i>Чтобы просмотреть текущее описание, вернитесь назад</i>"),
                sep="",
            ),
            Case(
                {
                    True: Const("<br><br>⚠️ <b>Описание не может быть пустым</b>"),
                    False: Const("")
                },
                selector="has_void_description"
            ),
            Case(
                {
                    True: Const("<br><br>📏 <b>Слишком короткое описание</b><br><i>Минимум 10 символов</i>"),
                    False: Const("")
                },
                selector="has_small_description"
            ),
            Case(
                {
                    True: Const("<br><br>📏 <b>Слишком длинное описание</b><br><i>Максимум 2200 символов для Instagram</i>"),
                    False: Const("")
                },
                selector="has_big_description"
            ),

            TextInput(
                id="description_input",
                on_success=self.video_cut_moderation_service.handle_edit_description,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_preview),
            ),

            state=model.VideoCutModerationStates.edit_description,
            getter=self.video_cut_moderation_getter.get_edit_description_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_tags_window(self) -> Window:
        return Window(
            Multi(
                Const("🏷️ <b>Изменение тегов</b><br><br>"),
                Case(
                    {
                        True: Format("📋 <b>Текущие теги:</b><br><code>{current_tags}</code><br><br>"),
                        False: Const("📋 <b>Текущие теги:</b> <i>не указаны</i><br><br>"),
                    },
                    selector="has_tags"
                ),
                Const("✍️ <b>Введите теги через запятую:</b><br><br>"),
                Const("💡 <b>Пример:</b> <code>технологии, обучение, shorts</code><br><br>"),
                Const("📏 <b>Ограничения:</b><br>"),
                Const("🎬 YouTube: <code>максимум 15 тегов</code><br>"),
                Const("📱 Instagram: <code>максимум 30 хештегов</code><br><br>"),
                Const("🗑️ <i>Оставьте поле пустым для удаления всех тегов</i>"),
                sep="",
            ),
            Case(
                {
                    True: Const("<br><br>⚠️ <b>Теги не могут быть пустыми</b><br><i>Или оставьте поле пустым для удаления</i>"),
                    False: Const("")
                },
                selector="has_void_tags"
            ),

            TextInput(
                id="tags_input",
                on_success=self.video_cut_moderation_service.handle_edit_tags,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_preview),
            ),

            state=model.VideoCutModerationStates.edit_tags,
            getter=self.video_cut_moderation_getter.get_edit_tags_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_social_network_select_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Выбор социальных сетей для публикации</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Нет подключённых соцсетей!</b><br><br>"),
                            Const("🔗 <i>Для публикации видео необходимо подключить хотя бы одну социальную сеть.</i><br><br>"),
                            Const("👨‍💼 <b>Обратитесь к администратору</b> для настройки интеграции с соцсетями."),
                        ),
                        False: Multi(
                            Const("📱 <b>Выберите платформы для публикации:</b><br><br>"),
                            Const("💡 <i>Можно выбрать несколько платформ одновременно</i>"),
                        ),
                    },
                    selector="no_connected_networks"
                ),
                sep="",
            ),

            Column(
                Checkbox(
                    Const("✅ 🎬 YouTube Shorts"),
                    Const("⬜ 🎬 YouTube Shorts"),
                    id="youtube_checkbox",
                    default=False,
                    on_state_changed=self.video_cut_moderation_service.handle_toggle_social_network,
                    when="youtube_connected",
                ),
                Checkbox(
                    Const("✅ 📱 Instagram Reels"),
                    Const("⬜ 📱 Instagram Reels"),
                    id="instagram_checkbox",
                    default=False,
                    on_state_changed=self.video_cut_moderation_service.handle_toggle_social_network,
                    when="instagram_connected",
                ),
                when="has_available_networks",
            ),

            Button(
                Const("◀️ Назад к модерации"),
                id="back_to_video_cut_list_no_networks",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.moderation_list),
            ),

            state=model.VideoCutModerationStates.social_network_select,
            getter=self.video_cut_moderation_getter.get_social_network_select_data,
            parse_mode=SULGUK_PARSE_MODE,
        )