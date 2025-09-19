# internal/controller/tg/dialog/video_cut_draft_content/dialog.py
from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Checkbox
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

from internal import interface, model


class VideoCutsDraftDialog(interface.IVideoCutsDraftDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            video_cut_draft_service: interface.IVideoCutsDraftDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.video_cut_draft_service = video_cut_draft_service

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
        """Окно списка черновиков видео-нарезок с отображением видео"""
        return Window(
            Multi(
                Const("📹 <b>Мои черновики видео</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Format("📊 Всего черновиков: <b>{video_cuts_count}</b>\n"),
                            Format("📅 Период: <b>{period_text}</b>\n\n"),
                            # Отображаем видео ПЕРЕД информацией о нарезке
                            Case(
                                {
                                    True: Const("🎬 <b>Превью видео:</b>\n"),
                                    False: Const("⚠️ <i>Видео недоступно</i>\n"),
                                },
                                selector="has_video"
                            ),
                            Const("━━━━━━━━━━━━━━━━━━━━\n"),
                            # Информация о текущей нарезке
                            Format("🎬 <b>{video_name}</b>\n\n"),
                            Format("{video_description}\n\n"),
                            Case(
                                {
                                    True: Format("🏷 Теги: {video_tags}\n"),
                                    False: Const("🏷 Теги: <i>отсутствуют</i>\n"),
                                },
                                selector="has_tags"
                            ),
                            Format("📹 Источник: {youtube_reference_short}\n"),
                            Format("📅 Создано: {created_at}\n"),
                            # Информация о настройках публикации с реальным статусом
                            Const("\n🌐 <b>Подключенные социальные сети:</b>\n"),
                            Case(
                                {
                                    True: Case(
                                        {
                                            True: Const("📺 YouTube Shorts: ✅ (выбрано)\n"),
                                            False: Const("📺 YouTube Shorts: ✅ (не выбрано)\n"),
                                        },
                                        selector="youtube_selected"
                                    ),
                                    False: Const("📺 YouTube Shorts: ❌ (не подключен)\n"),
                                },
                                selector="youtube_connected"
                            ),
                            Case(
                                {
                                    True: Case(
                                        {
                                            True: Const("📸 Instagram Reels: ✅ (выбрано)"),
                                            False: Const("📸 Instagram Reels: ✅ (не выбрано)"),
                                        },
                                        selector="instagram_selected"
                                    ),
                                    False: Const("📸 Instagram Reels: ❌ (не подключен)"),
                                },
                                selector="instagram_connected"
                            ),
                            Const("\n━━━━━━━━━━━━━━━━━━━━"),
                        ),
                        False: Multi(
                            Const("📂 <b>Нет черновиков видео</b>\n\n"),
                            Const("<i>Создайте первую видео-нарезку для работы с черновиками</i>"),
                        ),
                    },
                    selector="has_video_cuts"
                ),
                sep="",
            ),

            # Добавляем динамическое медиа для отображения видео
            DynamicMedia(
                "video_media",
                when="has_video"
            ),

            # Навигация со счетчиком
            Row(
                Button(
                    Const("⬅️"),
                    id="prev_video_cut",
                    on_click=self.video_cut_draft_service.handle_navigate_video_cut,
                    when="has_prev",
                ),
                Button(
                    Format("{current_index}/{video_cuts_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer("📊 Навигация по черновикам"),
                    when="has_video_cuts",
                ),
                Button(
                    Const("➡️"),
                    id="next_video_cut",
                    on_click=self.video_cut_draft_service.handle_navigate_video_cut,
                    when="has_next",
                ),
                when="has_video_cuts",
            ),

            # Основные действия
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
                    Const("📤 На модерацию"),
                    id="send_to_moderation",
                    on_click=self.video_cut_draft_service.handle_send_to_moderation,
                    when="not_can_publish",  # инвертированное условие
                ),
                Button(
                    Const("🚀 Опубликовать"),
                    id="publish_now",
                    on_click=self.video_cut_draft_service.handle_publish_now,
                    when="can_publish",
                ),
                Row(
                    Button(
                        Const("🗑 Удалить"),
                        id="delete",
                        on_click=self.video_cut_draft_service.handle_delete_video_cut,
                        when="has_video_cuts",
                    ),
                ),
                when="has_video_cuts",
            ),

            Row(
                Button(
                    Const("◀️ В меню контента"),
                    id="back_to_content_menu",
                    on_click=self.video_cut_draft_service.handle_back_to_content_menu,
                ),
            ),

            state=model.VideoCutsDraftStates.video_cut_list,
            getter=self.video_cut_draft_service.get_video_cut_list_data,
            parse_mode="HTML",
        )

    def get_edit_preview_window(self) -> Window:
        """Окно редактирования с превью видео-нарезки"""
        return Window(
            Multi(
                Const("✏️ <b>Редактирование видео</b>\n\n"),
                # Сначала показываем само видео
                Case(
                    {
                        True: Const("🎬 <b>Превью видео:</b>\n"),
                        False: Const("⚠️ <i>Видео недоступно</i>\n"),
                    },
                    selector="has_video"
                ),
                Const("━━━━━━━━━━━━━━━━━━━━\n"),
                Format("📅 Создано: {created_at}\n"),
                Format("📹 Источник: {youtube_reference}\n\n"),
                Const("━━━━━━━━━━━━━━━━━━━━\n"),
                Format("🎬 <b>{video_name}</b>\n\n"),
                Format("{video_description}\n\n"),
                Case(
                    {
                        True: Format("🏷 Теги: {video_tags}"),
                        False: Const("🏷 Теги: <i>отсутствуют</i>"),
                    },
                    selector="has_tags"
                ),
                Case(
                    {
                        True: Const("\n\n<i>❗️ Есть несохраненные изменения</i>"),
                        False: Const(""),
                    },
                    selector="has_changes"
                ),
                Const("\n━━━━━━━━━━━━━━━━━━━━\n\n"),
                Const("📌 <b>Выберите, что изменить:</b>"),
                sep="",
            ),

            # Добавляем медиа и в окно редактирования
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
                    Const("🏷 Изменить теги"),
                    id="edit_tags",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_tags),
                ),
                Button(
                    Const("🌐 Выбрать соцсети"),
                    id="social_network_select",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.social_network_select),
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
                    Const("◀️ Назад"),
                    id="back_to_video_cut_list",
                    on_click=self.video_cut_draft_service.handle_back_to_video_cut_list,
                ),
            ),

            state=model.VideoCutsDraftStates.edit_preview,
            getter=self.video_cut_draft_service.get_edit_preview_data,
            parse_mode="HTML",
        )

    def get_edit_title_window(self) -> Window:
        """Окно редактирования названия видео"""
        return Window(
            Multi(
                Const("📝 <b>Изменение названия видео</b>\n\n"),
                Format("Текущее: <b>{current_title}</b>\n\n"),
                Const("✍️ <b>Введите новое название:</b>\n"),
                Const("<i>Максимум 100 символов для YouTube Shorts</i>\n"),
                Const("<i>Максимум 2200 символов для Instagram Reels</i>"),
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
            getter=self.video_cut_draft_service.get_edit_title_data,
            parse_mode="HTML",
        )

    def get_edit_description_window(self) -> Window:
        """Окно редактирования описания видео"""
        return Window(
            Multi(
                Const("📄 <b>Изменение описания видео</b>\n\n"),
                Format("Длина текущего описания: <b>{current_description_length}</b> символов\n\n"),
                Const("✍️ <b>Введите новое описание:</b>\n"),
                Const("<i>Максимум 5000 символов для YouTube</i>\n"),
                Const("<i>Максимум 2200 символов для Instagram</i>\n"),
                Const("<i>Для просмотра текущего описания вернитесь назад</i>"),
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
            getter=self.video_cut_draft_service.get_edit_description_data,
            parse_mode="HTML",
        )

    def get_edit_tags_window(self) -> Window:
        """Окно редактирования тегов видео"""
        return Window(
            Multi(
                Const("🏷 <b>Изменение тегов видео</b>\n\n"),
                Case(
                    {
                        True: Format("Текущие теги: <b>{current_tags}</b>\n\n"),
                        False: Const("Теги отсутствуют\n\n"),
                    },
                    selector="has_tags"
                ),
                Const("✍️ <b>Введите теги через запятую:</b>\n"),
                Const("<i>Например: технологии, обучение, shorts</i>\n"),
                Const("<i>Максимум 15 тегов для YouTube</i>\n"),
                Const("<i>Максимум 30 хештегов для Instagram</i>\n"),
                Const("<i>Оставьте пустым для удаления всех тегов</i>"),
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
            getter=self.video_cut_draft_service.get_edit_tags_data,
            parse_mode="HTML",
        )

    def get_social_network_select_window(self) -> Window:
        """Окно выбора социальных сетей для публикации"""
        return Window(
            Multi(
                Const("🌐 <b>Выбор социальных сетей</b>\n\n"),
                Const("📋 <b>Доступные социальные сети для видео-нарезок:</b>\n"),
                Case(
                    {
                        True: Multi(
                            Const("📺 YouTube Shorts - <b>подключен</b>\n"),
                            Const("📸 Instagram Reels - <b>подключен</b>\n\n"),
                            Const("✅ <b>Выберите, где опубликовать:</b>"),
                        ),
                        False: Multi(
                            Case(
                                {
                                    True: Const("📺 YouTube Shorts - <b>подключен</b>\n"),
                                    False: Const("📺 YouTube Shorts - <b>не подключен</b>\n"),
                                },
                                selector="youtube_connected"
                            ),
                            Case(
                                {
                                    True: Const("📸 Instagram Reels - <b>подключен</b>\n\n"),
                                    False: Const("📸 Instagram Reels - <b>не подключен</b>\n\n"),
                                },
                                selector="instagram_connected"
                            ),
                            Case(
                                {
                                    True: Const("⚠️ <b>Нет подключенных социальных сетей!</b>\n"),
                                    False: Const("✅ <b>Выберите, где опубликовать:</b>"),
                                },
                                selector="no_connected_networks"
                            ),
                        ),
                    },
                    selector="all_networks_connected"
                ),
                sep="",
            ),

            # Чекбоксы для выбора платформ (только для подключенных)
            Column(
                Checkbox(
                    Const("📺 YouTube Shorts"),
                    Const("✅ YouTube Shorts"),
                    id="youtube_checkbox",
                    default=True,
                    on_state_changed=self.video_cut_draft_service.handle_toggle_social_network,
                    when="youtube_connected",
                ),
                Checkbox(
                    Const("📸 Instagram Reels"),
                    Const("✅ Instagram Reels"),
                    id="instagram_checkbox",
                    default=True,
                    on_state_changed=self.video_cut_draft_service.handle_toggle_social_network,
                    when="instagram_connected",
                ),
            ),

            # Предупреждение если нет подключенных сетей
            Case(
                {
                    True: Multi(
                        Const(
                            "\n🔗 <i>Для публикации видео-нарезок необходимо подключить хотя бы одну социальную сеть в настройках организации.</i>"),
                    ),
                    False: Const(""),
                },
                selector="no_connected_networks"
            ),

            Button(
                Const("◀️ Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutsDraftStates.edit_preview),
            ),

            state=model.VideoCutsDraftStates.social_network_select,
            getter=self.video_cut_draft_service.get_social_network_select_data,
            parse_mode="HTML",
        )