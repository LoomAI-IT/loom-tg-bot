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
                # Возвращаем пустые данные, так как вся информация статична в диалоге
                data = {}

                self.logger.info("Данные окна ввода YouTube ссылки загружены")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                return {}