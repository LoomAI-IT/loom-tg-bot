from aiogram.types import Message, BotCommand
from aiogram import Dispatcher, Bot
from opentelemetry.trace import SpanKind, StatusCode

from internal import model, interface, common


class CommandController(interface.ICommandController):

    def __init__(
            self,
            tel: interface.ITelemetry,
            dp: Dispatcher,
            bot: Bot,
            state_service: interface.IStateService
    ):
        self.logger = tel.logger()
        self.tracer = tel.tracer()
        self.dp = dp
        self.bot = bot
        self.state_service = state_service

    async def start_handler(self, message: Message, user_state: model.State):
        with self.tracer.start_as_current_span(
                "CommandController.start_handler",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await message.answer("Привет")
                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise err

