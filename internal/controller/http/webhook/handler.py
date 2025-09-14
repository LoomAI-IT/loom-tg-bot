from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update, ReplyKeyboardMarkup, KeyboardButton
from fastapi import Header
from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import interface, common
from .model import *


class TelegramWebhookController(interface.ITelegramWebhookController):
    def __init__(
            self,
            tel: interface.ITelemetry,
            dp: Dispatcher,
            bot: Bot,
            domain: str,
            prefix: str,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

        self.dp = dp
        self.bot = bot
        self.domain = domain
        self.prefix = prefix

    async def bot_webhook(
            self,
            update: dict,
            x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None
    ):
        with self.tracer.start_as_current_span(
                "TelegramWebhookController.bot_webhook",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                if x_telegram_bot_api_secret_token != "secret":
                    return {"status": "error", "message": "Wrong secret token !"}

                telegram_update = Update(**update)
                await self.dp.feed_webhook_update(
                    bot=self.bot,
                    update=telegram_update)

                span.set_status(Status(StatusCode.OK))
                return None
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def bot_set_webhook(self):
        with self.tracer.start_as_current_span(
                "TelegramWebhookController.bot_set_webhook",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await self.bot.set_webhook(
                    f'https://{self.domain}{self.prefix}/update',
                    secret_token='secret',
                    allowed_updates=["message", "callback_query"],
                )
                webhook_info = await self.bot.get_webhook_info()

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

