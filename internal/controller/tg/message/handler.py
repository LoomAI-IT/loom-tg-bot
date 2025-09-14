import io

from aiogram import Bot
from aiogram.types import Message
from opentelemetry.trace import SpanKind, StatusCode

from internal import model, interface, common


class MessageController(interface.IMessageController):

    def __init__(
            self,
            bot: Bot,
            tel: interface.ITelemetry,
            state_service: interface.IStateService,
            storage: interface.IStorage,
    ):
        self.bot = bot
        self.logger = tel.logger()
        self.tracer = tel.tracer()
        self.state_service = state_service
        self.storage = storage

    async def message_handler(self, message: Message, user_state: model.State):
        with self.tracer.start_as_current_span(
                "MessageController.message_handler",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise err
