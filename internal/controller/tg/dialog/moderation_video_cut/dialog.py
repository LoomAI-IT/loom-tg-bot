from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column, Row, Checkbox
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

from internal import interface, model


class VideoCutModerationDialog(interface.IVideoCutModerationDialog):

    def __init__(
            self,
            tel: interface.ITelemetry,
            video_cut_moderation_service: interface.IVideoCutModerationDialogService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.video_cut_moderation_service = video_cut_moderation_service

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
        """Окно списка видео-нарезок на модерации с отображением видео"""
        return Window(
            Multi(
                Const("📹 <b>Модерация видео-нарезок</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Format("📊 Всего на модерации: <b>{video_cuts_count}</b>\n"),
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
                            Format("👤 Автор: <b>{author_name}</b>\n"),
                            Format("📅 Создано: {created_at}\n"),
                            Case(
                                {
                                    True: Format("⏰ Ожидает модерации: <b>{waiting_time}</b>\n"),
                                    False: Const(""),
                                },
                                selector="has_waiting_time"
                            ),
                            Format("📹 Источник: {youtube_reference}\n\n"),
                            Const("━━━━━━━━━━━━━━━━━━━━\n"),
                            Format("🎬 <b>{video_name}</b>\n\n"),
                            Format("{video_description}\n\n"),
                            Case(
                                {
                                    True: Format("🏷 Теги: {video_tags}\n"),
                                    False: Const("🏷 Теги: <i>отсутствуют</i>\n"),
                                },
                                selector="has_tags"
                            ),
                            Const("━━━━━━━━━━━━━━━━━━━━"),
                        ),
                        False: Multi(
                            Const("✅ <b>Нет видео-нарезок на модерации</b>\n\n"),
                            Const("<i>Все видео обработаны или еще не поступали</i>"),
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

            # Навигация со счетчиком в одной строке
            Row(
                Button(
                    Const("⬅️"),
                    id="prev_video_cut",
                    on_click=self.video_cut_moderation_service.handle_navigate_video_cut,
                    when="has_prev",
                ),
                Button(
                    Format("{current_index}/{total_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer(),  # Просто показываем позицию
                    when="has_video_cuts",
                ),
                Button(
                    Const("➡️"),
                    id="next_video_cut",
                    on_click=self.video_cut_moderation_service.handle_navigate_video_cut,
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
                        on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_preview),
                        when="has_video_cuts",
                    ),
                    Button(
                        Const("✅ Опубликовать"),
                        id="approve",
                        on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.social_network_select),
                        when="has_video_cuts",
                    ),
                ),
                Row(
                    Button(
                        Const("💬 Отклонить"),
                        id="reject_with_comment",
                        on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.reject_comment),
                        when="has_video_cuts",
                    ),
                ),
                when="has_video_cuts",
            ),

            Row(
                Button(
                    Const("◀️ В меню контента"),
                    id="back_to_content_menu",
                    on_click=self.video_cut_moderation_service.handle_back_to_content_menu,
                ),
            ),

            state=model.VideoCutModerationStates.moderation_list,
            getter=self.video_cut_moderation_service.get_moderation_list_data,
            parse_mode="HTML",
        )

    def get_reject_comment_window(self) -> Window:
        """Окно ввода комментария при отклонении видео-нарезки"""
        return Window(
            Multi(
                Const("❌ <b>Отклонение видео-нарезки</b>\n\n"),
                Format("🎬 Видео: <b>{video_name}</b>\n"),
                Format("👤 Автор: <b>{author_name}</b>\n\n"),
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
                    Const("Назад"),
                    id="back_to_moderation_list",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.moderation_list),
                ),
            ),

            state=model.VideoCutModerationStates.reject_comment,
            getter=self.video_cut_moderation_service.get_reject_comment_data,
            parse_mode="HTML",
        )

    def get_edit_preview_window(self) -> Window:
        """Окно редактирования с превью видео-нарезки"""
        return Window(
            Multi(
                Const("✏️ <b>Редактирование видео-нарезки</b>\n\n"),
                # Сначала показываем само видео
                Case(
                    {
                        True: Const("🎬 <b>Превью видео:</b>\n"),
                        False: Const("⚠️ <i>Видео недоступно</i>\n"),
                    },
                    selector="has_video"
                ),
                Const("━━━━━━━━━━━━━━━━━━━━\n"),
                Format("👤 Автор: <b>{author_name}</b>\n"),
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
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_title),
                ),
                Button(
                    Const("📄 Изменить описание"),
                    id="edit_description",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_description),
                ),
                Button(
                    Const("🏷 Изменить теги"),
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
                    Const("Назад"),
                    id="back_to_moderation_list",
                    on_click=self.video_cut_moderation_service.handle_back_to_moderation_list,
                ),
            ),

            state=model.VideoCutModerationStates.edit_preview,
            getter=self.video_cut_moderation_service.get_edit_preview_data,
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
                on_success=self.video_cut_moderation_service.handle_edit_title_save,
            ),

            Button(
                Const("Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_preview),
            ),

            state=model.VideoCutModerationStates.edit_title,
            getter=self.video_cut_moderation_service.get_edit_title_data,
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
                on_success=self.video_cut_moderation_service.handle_edit_description_save,
            ),

            Button(
                Const("Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_preview),
            ),

            state=model.VideoCutModerationStates.edit_description,
            getter=self.video_cut_moderation_service.get_edit_description_data,
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
                on_success=self.video_cut_moderation_service.handle_edit_tags_save,
            ),

            Button(
                Const("Назад"),
                id="back_to_edit_preview",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.edit_preview),
            ),

            state=model.VideoCutModerationStates.edit_tags,
            getter=self.video_cut_moderation_service.get_edit_tags_data,
            parse_mode="HTML",
        )

    def get_social_network_select_window(self) -> Window:
        """Окно выбора социальных сетей для публикации видео"""
        return Window(
            Multi(
                Const("🌐 <b>Выбор социальных сетей</b>\n\n"),
                Case(
                    {
                        True: Multi(
                            Const("⚠️ <b>Нет подключенных видео-платформ!</b>\n\n"),
                            Const(
                                "🔗 <i>Для публикации видео-нарезок необходимо подключить хотя бы одну видео-платформу в настройках организации.</i>\n\n"),
                            Const("Обратитесь к администратору для подключения YouTube или Instagram."),
                        ),
                        False: Multi(
                            Const("📋 <b>Доступные видео-платформы:</b>\n\n"),
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
                    Const("✅ YouTube Shorts"),
                    Const("❌ YouTube Shorts"),
                    id="youtube_checkbox",
                    default=False,
                    on_state_changed=self.video_cut_moderation_service.handle_toggle_social_network,
                    when="youtube_connected",
                ),
                Checkbox(
                    Const("✅ Instagram Reels"),
                    Const("❌ Instagram Reels"),
                    id="instagram_checkbox",
                    default=False,
                    on_state_changed=self.video_cut_moderation_service.handle_toggle_social_network,
                    when="instagram_connected",
                ),
                when="has_available_networks",
            ),

            # Кнопки действий
            Row(
                Button(
                    Const("🚀 Опубликовать"),
                    id="publish_with_networks",
                    on_click=self.video_cut_moderation_service.handle_publish_with_selected_networks,
                    when="has_available_networks",
                ),
                Button(
                    Const("◀️ Назад"),
                    id="back_to_moderation_list",
                    on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.moderation_list),
                ),
            ),

            # Кнопка назад для случая когда нет доступных сетей
            Button(
                Const("◀️ Назад к списку"),
                id="back_to_moderation_list_no_networks",
                on_click=lambda c, b, d: d.switch_to(model.VideoCutModerationStates.moderation_list),
                when="no_connected_networks",
            ),

            state=model.VideoCutModerationStates.social_network_select,
            getter=self.video_cut_moderation_service.get_social_network_select_data,
            parse_mode="HTML",
        )