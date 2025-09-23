from aiogram_dialog import DialogManager

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface


class GenerateVideoCutGetter(interface.IGenerateVideoCutGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

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
                data = {
                    "youtube_url": dialog_manager.dialog_data.get("youtube_url", ""),
                    "has_invalid_youtube_url": dialog_manager.dialog_data.get("has_invalid_youtube_url", False),
                    "has_processing_error": dialog_manager.dialog_data.get("has_processing_error", False),
                    "has_youtube_url": dialog_manager.dialog_data.get("has_youtube_url", False),
                    "is_processing_video": dialog_manager.dialog_data.get("is_processing_video", False),
                }

                self.logger.info("Данные окна ввода YouTube ссылки загружены")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                return {}