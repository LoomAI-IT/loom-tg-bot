from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Multi, Case
from aiogram_dialog.widgets.kbd import Button, Column
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class AlertsDialog(interface.IAlertsDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            alerts_service: interface.IAlertsService,
            alerts_getter: interface.IAlertsGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.alerts_service = alerts_service
        self.alerts_getter = alerts_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_video_generated_alert_window(),
            self.get_publication_approved_alert_window()
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
                    on_click=self.alerts_service.handle_go_to_video_drafts,
                ),
                Button(
                    Const("🏠 Главное меню"),
                    id="to_main_menu_from_video_cut_alert",
                    on_click=self.alerts_service.handle_go_to_main_menu,
                ),
            ),

            state=model.AlertsStates.video_generated_alert,
            getter=self.alerts_getter.get_video_alert_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_publication_approved_alert_window(self) -> Window:
        return Window(
            Multi(
                Case(
                    {
                        True: Multi(
                            Const("🎉 <b>Ваши публикации приняты модератором!</b><br><br>"),
                            Format("📊 Опубликовано <b>{alerts_count}</b> {alerts_word}:<br><br>"),
                            Format("📋 <b>Список публикаций:</b><br>{publications_text}"),
                        ),
                        False: Multi(
                            Const("🎉 <b>Публикация одобрена модератором!</b><br>"),
                            Format("{publication_text}<br>"),
                            Case(
                                {
                                    True: Multi(
                                        Const("<br>🔗 <b>Ссылки на ваши посты:</b><br>"),
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
                                    ),
                                    False: Const("<br>📝 <i>Публикация размещена, но ссылки пока недоступны</i>"),
                                },
                                selector="has_post_links"
                            ),
                        ),
                    },
                    selector="has_multiple_alerts"
                ),
                sep="",
            ),

            Column(
                Button(
                    Const("🏠 Главное меню"),
                    id="to_main_menu_from_publication_approved_alert",
                    on_click=self.alerts_service.handle_go_to_main_menu,
                ),
            ),

            state=model.AlertsStates.publication_approved_alert,
            getter=self.alerts_getter.get_publication_approved_alert_data,
            parse_mode=SULGUK_PARSE_MODE,
        )
