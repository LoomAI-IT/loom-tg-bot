from aiogram_dialog import Window, Dialog, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Checkbox
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

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
                Const("🎬 <b>Твои видео-нарезки</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Format("📽️ <b>{video_name}</b>\n"),
                            Format("📝 {video_description}\n\n"),
                            Case(
                                {
                                    True: Format("🏷️ <b>Теги:</b> <code>{video_tags}</code>\n"),
                                    False: Const("🏷️ <b>Теги:</b> <i>❌ отсутствуют</i>\n"),
                                },
                                selector="has_tags"
                            ),
                            Format("🔗 <b>Источник:</b> <a href='{youtube_reference}'>YouTube</a>\n\n"),
                            Format("📅 <b>Создано:</b> <code>{created_at}</code>\n"),
                        ),
                        False: Multi(
                            Const("📂 <b>Пусто в черновиках</b>\n\n"),
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
            parse_mode="HTML",
        )

    def get_edit_preview_window(self) -> Window:
        return Window(
            Multi(
                Const("✏️ <b>Редактирование видео</b>\n\n"),

                Format("📽️ <b>{video_name}</b>\n\n"),
                Format("📝 {video_description}\n\n"),
                Case(
                    {
                        True: Format("🏷️ <b>Теги:</b> <code>{video_tags}</code>\n"),
                        False: Const("🏷️ <b>Теги:</b> <i>❌ отсутствуют</i>\n"),
                    },
                    selector="has_tags"
                ),
                Format("🔗 <b>Источник:</b> <a href='{youtube_reference}'>YouTube</a>\n\n"),
                Format("📅 <b>Создано:</b> <code>{created_at}</code>\n"),
                Case(
                    {
                        True: Const("\n\n⚠️ <b><i>Есть несохраненные изменения!</i></b>"),
                        False: Const(""),
                    },
                    selector="has_changes"
                ),
                Const("\n\n📌 <b>Что будем изменять?</b>"),
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
            parse_mode="HTML",
        )

    def get_edit_title_window(self) -> Window:
        return Window(
            Multi(
                Const("📝 <b>Изменение названия</b>\n\n"),
                Format("📋 <b>Текущее название:</b>\n<i>{current_title}</i>\n\n"),
                Const("✍️ <b>Введите новое название:</b>\n\n"),
                Const("📏 <b>Ограничения по символам:</b>\n"),
                Const("🎬 YouTube Shorts: <code>максимум 100 символов</code>\n"),
                Const("📱 Instagram Reels: <code>максимум 2200 символов</code>"),
                sep="",
            ),

            TextInput(
                id="title_input",
                on_success=self.video_cut_draft_service.handle_edit_title_save,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_preview),
            ),

            state=model.VideoCutsDraftStates.edit_title,
            getter=self.video_cut_draft_getter.get_edit_title_data,
            parse_mode="HTML",
        )

    def get_edit_description_window(self) -> Window:
        """Окно редактирования описания видео"""
        return Window(
            Multi(
                Const("📄 <b>Изменение описания</b>\n\n"),
                Format("📊 <b>Длина текущего описания:</b> <code>{current_description_length} символов</code>\n\n"),
                Const("✍️ <b>Введите новое описание:</b>\n\n"),
                Const("📏 <b>Ограничения по символам:</b>\n"),
                Const("🎬 YouTube: <code>максимум 5000 символов</code>\n"),
                Const("📱 Instagram: <code>максимум 2200 символов</code>\n\n"),
                Const("💡 <i>Чтобы просмотреть текущее описание, вернитесь назад</i>"),
                sep="",
            ),

            TextInput(
                id="description_input",
                on_success=self.video_cut_draft_service.handle_edit_description_save,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_preview),
            ),

            state=model.VideoCutsDraftStates.edit_description,
            getter=self.video_cut_draft_getter.get_edit_description_data,
            parse_mode="HTML",
        )

    def get_edit_tags_window(self) -> Window:
        return Window(
            Multi(
                Const("🏷️ <b>Изменение тегов</b>\n\n"),
                Case(
                    {
                        True: Format("📋 <b>Текущие теги:</b>\n<code>{current_tags}</code>\n\n"),
                        False: Const("📋 <b>Текущие теги:</b> <i>❌ отсутствуют</i>\n\n"),
                    },
                    selector="has_tags"
                ),
                Const("✍️ <b>Введите теги через запятую:</b>\n\n"),
                Const("💡 <b>Пример:</b> <code>технологии, обучение, shorts</code>\n\n"),
                Const("📏 <b>Ограничения:</b>\n"),
                Const("🎬 YouTube: <code>максимум 15 тегов</code>\n"),
                Const("📱 Instagram: <code>максимум 30 хештегов</code>\n\n"),
                Const("🗑️ <i>Оставьте пустым для удаления всех тегов</i>"),
                sep="",
            ),

            TextInput(
                id="tags_input",
                on_success=self.video_cut_draft_service.handle_edit_tags_save,
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_preview),
            ),

            state=model.VideoCutsDraftStates.edit_tags,
            getter=self.video_cut_draft_getter.get_edit_tags_data,
            parse_mode="HTML",
        )

    def get_social_network_select_window(self) -> Window:
        return Window(
            Multi(
                Const("🌐 <b>Выбор социальных сетей</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Нет подключенных соцсетей!</b>\n\n"),
                            Const(
                                "🔗 <i>Для публикации видео-нарезок необходимо подключить хотя бы одну социальную сеть в настройках организации.</i>\n\n"),
                            Const("👨‍💼 Обратитесь к администратору для подключения социальных сетей."),
                        ),
                        False: Multi(
                            Const("📱 <b>Выберите платформы для публикации:</b>\n\n"),
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
                when="no_connected_networks",
            ),

            state=model.VideoCutsDraftStates.social_network_select,
            getter=self.video_cut_draft_getter.get_social_network_select_data,
            parse_mode="HTML",
        )
