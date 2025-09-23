from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram_dialog import BgManagerFactory
from fastapi import Header
from opentelemetry.trace import Status, StatusCode, SpanKind
from starlette.responses import JSONResponse

from internal import interface, common
from .model import *


class TelegramWebhookController(interface.ITelegramWebhookController):
    def __init__(
            self,
            tel: interface.ITelemetry,
            dp: Dispatcher,
            bot: Bot,
            state_service: interface.IStateService,
            dialog_bg_factory: BgManagerFactory,
            domain: str,
            prefix: str,
            interserver_secret_key: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

        self.dp = dp
        self.bot = bot
        self.state_service = state_service
        self.dialog_bg_factory = dialog_bg_factory

        self.domain = domain
        self.prefix = prefix
        self.interserver_secret_key = interserver_secret_key

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

    async def notify_employee_added(
            self,
            body: EmployeeNotificationBody,
    ) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "NotificationWebhookController.notify_employee_added",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Проверяем секретный ключ
                if body.interserver_secret_key != self.interserver_secret_key:
                    return JSONResponse(
                        content={"status": "error", "message": "Wrong secret token !"},
                        status_code=401
                    )

                # Получаем состояние пользователя по account_id
                user_state = (await self.state_service.state_by_account_id(
                    body.account_id
                ))[0]

                # Обновляем organization_id в состоянии пользователя
                await self.state_service.change_user_state(
                    user_state.id,
                    organization_id=body.organization_id
                )

                # Формируем сообщение
                message_text = self._format_notification_message(body)

                # Отправляем уведомление
                await self.bot.send_message(
                    chat_id=user_state.tg_chat_id,
                    text=message_text,
                    parse_mode="HTML"
                )

                self.logger.info(
                    "Уведомление о добавлении в организацию отправлено",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: user_state.tg_chat_id,
                        "account_id": body.account_id,
                        "organization_id": body.organization_id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    content={"status": "ok"},
                    status_code=200
                )


            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def notify_vizard_video_cut_generated(
            self,
            body: NotifyVizardVideoCutGenerated,
    ) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "NotificationWebhookController.notify_vizard_video_cut_generated",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Проверяем секретный ключ
                if body.interserver_secret_key != self.interserver_secret_key:
                    return JSONResponse(
                        content={"status": "error", "message": "Wrong secret token !"},
                        status_code=401
                    )

                # Получаем состояние пользователя по account_id
                user_state = (await self.state_service.state_by_account_id(
                    body.account_id
                ))[0]

                # Формируем сообщение для уведомления о генерации видео
                message_text = self._format_vizard_notification_message(body)

                # dialog_manager = self.dialog_bg_factory.bg(
                #     bot=self.bot,
                #     user_id=user_state.tg_chat_id,
                #     chat_id=user_state.tg_chat_id,
                # )

                await self.state_service.create_vizard_video_cut_alert(
                    state_id=user_state.id,
                    youtube_video_reference=body.youtube_video_reference,
                    video_count=body.video_count,
                )

                # Отправляем уведомление
                await self.bot.send_message(
                    chat_id=user_state.tg_chat_id,
                    text=message_text,
                    parse_mode="HTML"
                )

                self.logger.info(
                    "Уведомление о генерации видео отправлено",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: user_state.tg_chat_id,
                        "account_id": body.account_id,
                        "youtube_video_reference": body.youtube_video_reference,
                        "video_count": body.video_count,
                    }
                )

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    content={"status": "ok"},
                    status_code=200
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def set_cache_file(
            self,
            body: SetCacheFileBody,
    ) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "TelegramWebhookController.set_cache_file",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Проверяем секретный ключ
                if body.interserver_secret_key != self.interserver_secret_key:
                    return JSONResponse(
                        content={"status": "error", "message": "Wrong secret token !"},
                        status_code=401
                    )

                # Сохраняем файл в кеш
                await self.state_service.set_cache_file(
                    filename=body.filename,
                    file_id=body.file_id
                )

                self.logger.info(
                    "Файл сохранен в кеш",
                    {
                        "file_id": body.file_id,
                    }
                )

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    content={"status": "ok", "message": "File cached successfully"},
                    status_code=200
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                self.logger.error(
                    "Ошибка при сохранении файла в кеш",
                    {
                        "filename": body.filename,
                        "file_id": body.file_id,
                        "error": str(err)
                    }
                )
                return JSONResponse(
                    content={"status": "error", "message": "Failed to cache file"},
                    status_code=500
                )

    def _format_vizard_notification_message(self, body: NotifyVizardVideoCutGenerated) -> str:
        """Форматирует сообщение для уведомления о генерации видео"""
        video_word = "видео" if body.video_count == 1 else "видеороликов"

        message_text = (
            f"🎬 <b>Ваше видео готово!</b>\n\n"
            f"Успешно сгенерировано {body.video_count} {video_word} из видео:\n"
            f"📺 <a href='{body.youtube_video_reference}'>Исходное видео</a>\n\n"
            f"Перейдите в черновики, чтобы посмотреть результат!"
        )

        return message_text

    def _format_notification_message(self, body: EmployeeNotificationBody) -> str:
        role_names = {
            "employee": "Сотрудник",
            "moderator": "Модератор",
            "admin": "Администратор",
            "owner": "Владелец"
        }
        role_display = role_names.get(body.role, body.role)

        message_text = (
            f"🎉 <b>Добро пожаловать в команду!</b>\n\n"
            f"Вас добавили в организацию:\n"
            f"🏷 Ваша роль: <b>{role_display}</b>\n\n"
            f"Нажмите /start чтобы начать работу!"
        )

        return message_text