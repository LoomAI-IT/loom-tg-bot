from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Checkbox
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class VideoCutsDraftDialog(interface.IVideoCutsDraftDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            video_cut_draft_service: interface.IVideoCutsDraftService,
            video_cut_draft_getter: interface.IVideoCutsDraftGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.video_cut_draft_service = video_cut_draft_service
        self.video_cut_draft_getter = video_cut_draft_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_video_cut_list_window(),
            self.get_edit_preview_window(),
            self.get_edit_title_window(),
            self.get_edit_description_window(),
            self.get_edit_tags_window(),
            self.get_social_network_select_window(),
        )

    def get_video_cut_list_window(self) -> Window:
        return Window(
            Multi(
                Const("🎬 <b>Твои видео-нарезки</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Format("📽️ <b>{video_name}</b><br>"),
                            Format("📝 {video_description}<br><br>"),
                            Case(
                                {
                                    True: Format("🏷️ <b>Теги:</b> <code>{video_tags}</code><br>"),
                                    False: Const("🏷️ <b>Теги:</b> <i>❌ отсутствуют</i><br>"),
                                },
                                selector="has_tags"
                            ),
                            Format("🔗 <b>Источник:</b> <a href='{youtube_reference}'>YouTube</a><br><br>"),
                            Format("📅 <b>Создано:</b> <code>{created_at}</code><br>"),
                        ),
                        False: Multi(
                            Const("📂 <b>Пусто в черновиках</b><br><br>"),
                            Const("💡 <i>Создайте первую видео-нарезку, чтобы начать работу с черновиками</i>"),
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
                    on_click=self.video_cut_draft_service.handle_navigate_video_cut,
                    when="has_prev",
                ),
                Button(
                    Format("📊 {current_index}/{video_cuts_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer("📈 Навигация по черновикам"),
                    when="has_video_cuts",
                ),
                Button(
                    Const("➡️ След"),
                    id="next_video_cut",
                    on_click=self.video_cut_draft_service.handle_navigate_video_cut,
                    when="has_next",
                ),
                when="has_video_cuts",
            ),

            Column(
                Row(
                    Button(
                        Const("✏️ Редактировать"),
                        id="edit",
                        on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_preview),
                        when="has_video_cuts",
                    ),
                ),
                Button(
                    Const("📤 Отправить на модерацию"),
                    id="send_to_moderation",
                    on_click=self.video_cut_draft_service.handle_send_to_moderation,
                    when="not_can_publish",
                ),
                Button(
                    Const("🌐 Выбрать соцсети"),
                    id="select_social_network",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.social_network_select,
                                                         ShowMode.EDIT),
                    when="can_publish",
                ),
                Button(
                    Const("🚀 Опубликовать сейчас"),
                    id="publish_now",
                    on_click=self.video_cut_draft_service.handle_publish_now,
                    when="can_publish",
                ),
                Row(
                    Button(
                        Const("🗑️ Удалить"),
                        id="delete",
                        on_click=self.video_cut_draft_service.handle_delete_video_cut,
                        when="has_video_cuts",
                    ),
                ),
                when="has_video_cuts",
            ),

            Row(
                Button(
                    Const("◀️ Меню контента"),
                    id="back_to_content_menu",
                    on_click=self.video_cut_draft_service.handle_back_to_content_menu,
                ),
            ),

            state=model.VideoCutsDraftStates.video_cut_list,
            getter=self.video_cut_draft_getter.get_video_cut_list_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_preview_window(self) -> Window:
        return Window(
            Multi(
                Const("✏️ <b>Редактирование видео</b><br><br>"),

                Format("📽️ <b>{video_name}</b><br><br>"),
                Format("📝 {video_description}<br><br>"),
                Case(
                    {
                        True: Format("🏷️ <b>Теги:</b> <code>{video_tags}</code><br>"),
                        False: Const("🏷️ <b>Теги:</b> <i>❌ отсутствуют</i><br>"),
                    },
                    selector="has_tags"
                ),
                Format("🔗 <b>Источник:</b> <a href='{youtube_reference}'>YouTube</a><br><br>"),
                Format("📅 <b>Создано:</b> <code>{created_at}</code><br>"),
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
                "video_media",
                when="has_video"
            ),

            Column(
                Button(
                    Const("📝 Изменить название"),
                    id="edit_title",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_title),
                ),
                Button(
                    Const("📄 Изменить описание"),
                    id="edit_description",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_description),
                ),
                Button(
                    Const("🏷️ Изменить теги"),
                    id="edit_tags",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_tags),
                ),
            ),

            Row(
                Button(
                    Const("💾 Сохранить изменения"),
                    id="save_changes",
                    on_click=self.video_cut_draft_service.handle_save_changes,
                    when="has_changes",
                ),
                Button(
                    Const("◀️ Назад к списку"),
                    id="back_to_video_cut_list",
                    on_click=self.video_cut_draft_service.handle_back_to_video_cut_list,
                ),
            ),

            state=model.VideoCutsDraftStates.edit_preview,
            getter=self.video_cut_draft_getter.get_edit_preview_data,
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
                    True: Const("<br>❌ <b>Ошибка:</b> Название не может быть пустым"),
                    False: Const("")
                },
                selector="has_void_title"
            ),
            Case(
                {
                    True: Const("<br>📏 <b>Слишком короткое название</b><br><i>Минимум 5 символов</i>"),
                    False: Const("")
                },
                selector="has_small_title"
            ),
            Case(
                {
                    True: Const("<br>📏 <b>Слишком длинное название</b><br><i>Максимум 500 символов</i>"),
                    False: Const("")
                },
                selector="has_big_title"
            ),

            TextInput(
                id="title_input",
                on_success=self.video_cut_draft_service.handle_edit_title,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_preview),
            ),

            state=model.VideoCutsDraftStates.edit_title,
            getter=self.video_cut_draft_getter.get_edit_title_data,
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
                    True: Const("<br>❌ <b>Ошибка:</b> Описание не может быть пустым"),
                    False: Const("")
                },
                selector="has_void_description"
            ),
            Case(
                {
                    True: Const("<br>📏 <b>Слишком короткое описание</b><br><i>Минимум 5 символов</i>"),
                    False: Const("")
                },
                selector="has_small_description"
            ),
            Case(
                {
                    True: Const("<br>📏 <b>Слишком длинное описание</b><br><i>Максимум 500 символов</i>"),
                    False: Const("")
                },
                selector="has_big_description"
            ),

            TextInput(
                id="description_input",
                on_success=self.video_cut_draft_service.handle_edit_description,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_preview),
            ),

            state=model.VideoCutsDraftStates.edit_description,
            getter=self.video_cut_draft_getter.get_edit_description_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_edit_tags_window(self) -> Window:
        return Window(
            Multi(
                Const("🏷️ <b>Изменение тегов</b><br><br>"),
                Case(
                    {
                        True: Format("📋 <b>Текущие теги:</b><br><code>{current_tags}</code><br><br>"),
                        False: Const("📋 <b>Текущие теги:</b> <i>❌ отсутствуют</i><br><br>"),
                    },
                    selector="has_tags"
                ),
                Const("✍️ <b>Введите теги через запятую:</b><br><br>"),
                Const("💡 <b>Пример:</b> <code>технологии, обучение, shorts</code><br><br>"),
                Const("📏 <b>Ограничения:</b><br>"),
                Const("🎬 YouTube: <code>максимум 15 тегов</code><br>"),
                Const("📱 Instagram: <code>максимум 30 хештегов</code><br><br>"),
                Const("🗑️ <i>Оставьте пустым для удаления всех тегов</i>"),
                sep="",
            ),
            Case(
                {
                    True: Const("<br>❌ <b>Ошибка:</b> Тэги не может быть пустым"),
                    False: Const("")
                },
                selector="has_void_tags"
            ),

            TextInput(
                id="tags_input",
                on_success=self.video_cut_draft_service.handle_edit_tags,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_preview),
            ),

            state=model.VideoCutsDraftStates.edit_tags,
            getter=self.video_cut_draft_getter.get_edit_tags_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_social_network_select_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Выбор социальных сетей</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Нет подключенных соцсетей!</b><br><br>"),
                            Const(
                                "🔗 <i>Для публикации видео-нарезок необходимо подключить хотя бы одну социальную сеть в настройках организации.</i><br><br>"),
                            Const("👨‍💼 Обратитесь к администратору для подключения социальных сетей."),
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
                    Const("✅ 🎬 YouTube Shorts"),
                    Const("⬜ 🎬 YouTube Shorts"),
                    id="youtube_checkbox",
                    default=False,
                    on_state_changed=self.video_cut_draft_service.handle_toggle_social_network,
                    when="youtube_connected",
                ),
                Checkbox(
                    Const("✅ 📱 Instagram Reels"),
                    Const("⬜ 📱 Instagram Reels"),
                    id="instagram_checkbox",
                    default=False,
                    on_state_changed=self.video_cut_draft_service.handle_toggle_social_network,
                    when="instagram_connected",
                ),
                when="has_available_networks",
            ),

            Button(
                Const("◀️ Назад к списку"),
                id="back_to_video_cut_list_no_networks",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.video_cut_list),
            ),

            state=model.VideoCutsDraftStates.social_network_select,
            getter=self.video_cut_draft_getter.get_social_network_select_data,
            parse_mode=SULGUK_PARSE_MODE,
        )
