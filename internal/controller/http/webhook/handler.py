from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update, ReplyKeyboardMarkup, KeyboardButton
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
            domain: str,
            prefix: str,
            interserver_secret_key: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

        self.dp = dp
        self.bot = bot
        self.state_service = state_service

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
                        "organization_name": body.organization_name,

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

    def _format_notification_message(self, body: EmployeeNotificationBody) -> str:

        # Форматируем список разрешений
        permissions_list = []
        if body.permissions:
            if not body.permissions.get("required_moderation", True):
                permissions_list.append("✅ Публикации без модерации")
            if body.permissions.get("autoposting_permission", False):
                permissions_list.append("✅ Авто-постинг")
            if body.permissions.get("add_employee_permission", False):
                permissions_list.append("✅ Добавление сотрудников")
            if body.permissions.get("edit_employee_perm_permission", False):
                permissions_list.append("✅ Изменение разрешений")
            if body.permissions.get("top_up_balance_permission", False):
                permissions_list.append("✅ Пополнение баланса")
            if body.permissions.get("sign_up_social_net_permission", False):
                permissions_list.append("✅ Подключение соцсетей")

        if not permissions_list:
            permissions_list.append("❌ Базовые разрешения")

        permissions_text = "\n".join(permissions_list)

        # Получаем читаемое название роли
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
            f"🏢 <b>{body.organization_name}</b>\n\n"
            f"👤 Пригласил: <b>{body.invited_by_name}</b>\n"
            f"🏷 Ваша роль: <b>{role_display}</b>\n\n"
            f"📋 <b>Ваши разрешения:</b>\n"
            f"{permissions_text}\n\n"
            f"Нажмите /start чтобы начать работу!"
        )

        return message_text
