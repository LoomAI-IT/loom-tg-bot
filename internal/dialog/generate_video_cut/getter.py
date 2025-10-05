from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class GenerateVideoCutGetter(interface.IGenerateVideoCutGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo

    async def get_youtube_input_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "GenerateVideoCutGetter.get_youtube_input_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало загрузки данных окна ввода YouTube ссылки")

                is_processing_video = False
                if dialog_manager.start_data:
                    if dialog_manager.start_data.get("is_processing_video"):
                        self.logger.info("Видео в процессе обработки из start_data")
                        is_processing_video = True
                else:
                    is_processing_video = dialog_manager.dialog_data.get("is_processing_video", False)
                    if is_processing_video:
                        self.logger.info("Видео в процессе обработки из dialog_data")

                data = {
                    "is_processing_video": is_processing_video,
                    "has_invalid_youtube_url": dialog_manager.dialog_data.get("has_invalid_youtube_url", False),
                }

                self.logger.info("Завершение загрузки данных окна ввода YouTube ссылки")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def get_video_alert_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "GenerateVideoCutGetter.get_video_alert_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало загрузки данных алерта")

                state = await self._get_user_state(dialog_manager)

                alerts = await self.state_repo.get_vizard_video_cut_alert_by_state_id(state.id)

                if not alerts:
                    self.logger.info("Алерты не найдены")
                    span.set_status(Status(StatusCode.ERROR, "No alerts found"))
                    return {}

                alerts_count = len(alerts)
                has_multiple_alerts = alerts_count > 1

                if has_multiple_alerts:
                    self.logger.info("Обнаружено несколько алертов")
                    alerts_text_parts = []
                    for i, alert in enumerate(alerts, 1):
                        video_word = self._get_video_word(alert.video_count)
                        alerts_text_parts.append(
                            f"📺 <b>{i}.</b> {alert.video_count} {video_word} из видео:\n"
                            f"🔗 <a href='{alert.youtube_video_reference}'>Исходное видео</a>\n"
                        )

                    alerts_text = "\n".join(alerts_text_parts)
                    alerts_word = self._get_alerts_word(alerts_count)

                    data = {
                        "has_multiple_alerts": True,
                        "alerts_count": alerts_count,
                        "alerts_word": alerts_word,
                        "alerts_text": alerts_text,
                    }
                else:
                    self.logger.info("Обнаружен один алерт")
                    alert = alerts[0]
                    video_word = self._get_video_word(alert.video_count)

                    data = {
                        "has_multiple_alerts": False,
                        "video_count": alert.video_count,
                        "video_word": video_word,
                        "youtube_video_reference": alert.youtube_video_reference,
                    }

                self.logger.info("Завершение загрузки данных алерта")
                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def _get_user_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'callback_query') and dialog_manager.event.callback_query:
            chat_id = dialog_manager.event.callback_query.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state_list = await self.state_repo.state_by_id(chat_id)
        if not state_list:
            raise ValueError(f"State not found for chat_id: {chat_id}")

        return state_list[0]

    def _get_video_word(self, count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return "видео"
        elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            return "видео"
        else:
            return "видео"

    def _get_alerts_word(self, count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return "видео"
        elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            return "видео"
        else:
            return "видео"