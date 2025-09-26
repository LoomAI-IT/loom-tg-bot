from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.input import MessageInput
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class GenerateVideoCutDialog(interface.IGenerateVideoCutDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            generate_video_cut_service: interface.IGenerateVideoCutService,
            generate_video_cut_getter: interface.IGenerateVideoCutGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.generate_video_cut_service = generate_video_cut_service
        self.generate_video_cut_getter = generate_video_cut_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_youtube_link_input_window(),
            self.get_video_generated_alert_window(),
        )

    def get_youtube_link_input_window(self) -> Window:
        return Window(
            Multi(
                Case(
                    {
                        True: Multi(
                            Const("⏳ <b>Видео обрабатывается...</b><br><br>"),
                            Const("📬 <b>Я уведомлю вас, как только видео будут готовы!</b><br><br>"),
                        ),
                        False: Multi(
                            # Error messages
                            Case(
                                {
                                    True: Const("❌ <b>Ошибка:</b> <i>Неверная ссылка на YouTube</i><br><br>"),
                                    False: Const(""),
                                },
                                selector="has_invalid_youtube_url"
                            ),

                            # Instructions
                            Const("📋 <b>Инструкция:</b><br>"),
                            Const("┌ 🔗 Отправьте ссылку на YouTube видео<br>"),
                            Const("├ ✂️ Я создам из него короткие видео-нарезки<br>"),
                            Const("└ 📁 Готовые видео появятся в разделе <i>\"Черновики\"</i><br><br>"),
                            Const("🎯 <b>Введите ссылку на YouTube видео:</b><br>"),
                            Const("💡 <i>Например:</i> <code>https://www.youtube.com/watch?v=VIDEO_ID</code><br><br>"),

                        ),
                    },
                    selector="is_processing_video"
                ),
                sep="",
            ),

            MessageInput(
                func=self.generate_video_cut_service.handle_youtube_link_input,
                content_types=["text"],
            ),

            Column(
                Button(
                    Const("🏠 В меню контента"),
                    id="to_content_menu",
                    on_click=self.generate_video_cut_service.handle_go_to_content_menu,
                ),
            ),

            state=model.GenerateVideoCutStates.input_youtube_link,
            getter=self.generate_video_cut_getter.get_youtube_input_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_video_generated_alert_window(self) -> Window:
        """Окно со списком готовых видео"""
        return Window(
            Multi(
                Case(
                    {
                        True: Multi(
                            Const("🎉 <b>Ваши видео готовы!</b><br><br>"),
                            Format("📊 У вас готово <b>{alerts_count}</b> {alerts_word}:<br><br>"),
                            # Список всех алертов
                            Format("📋 <b>Список готовых видео:</b><br>{alerts_text}"),
                        ),
                        False: Multi(
                            Const("🎉 <b>Ваше видео готово!</b><br><br>"),
                            Format("✅ Успешно сгенерировано <b>{video_count}</b> {video_word} из видео:<br>"),
                            Format("🎬 <a href='{youtube_video_reference}'>📺 Исходное видео</a><br><br>"),
                        ),
                    },
                    selector="has_multiple_alerts"
                ),
                Const("👉 <u>Перейдите в черновики</u>, чтобы посмотреть результат! 🎯"),
                sep="",
            ),

            Column(
                Button(
                    Const("📝 Черновики нарезок"),
                    id="to_video_drafts_from_alert",
                    on_click=self.generate_video_cut_service.handle_go_to_video_drafts,
                ),
                Button(
                    Const("🏠 Главное меню"),
                    id="to_main_menu_from_alert",
                    on_click=self.generate_video_cut_service.handle_go_to_main_menu,
                ),
            ),

            state=model.GenerateVideoCutStates.video_generated_alert,
            getter=self.generate_video_cut_getter.get_video_alert_data,
            parse_mode=SULGUK_PARSE_MODE,
        )