from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram_dialog import BgManagerFactory, ShowMode, StartMode
from fastapi import Header
from starlette.responses import JSONResponse

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method
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

    @traced_method()
    async def bot_webhook(
            self,
            update: dict,
            x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None
    ):
        if x_telegram_bot_api_secret_token != "secret":
            return {"status": "error", "message": "Wrong secret token !"}

        telegram_update = Update(**update)
        await self.dp.feed_webhook_update(
            bot=self.bot,
            update=telegram_update
        )
        return None

    @auto_log()
    @traced_method()
    async def bot_set_webhook(self):
        await self.bot.set_webhook(
            f'https://{self.domain}{self.prefix}/update',
            secret_token='secret',
            allowed_updates=["message", "callback_query"],
        )

        # Устанавливаем короткое описание бота (показывается под именем)
        await self.bot.set_my_short_description(
            short_description="AI SMM инструмент для снижения затрат на рутину. От голосового сообщения до поста в соцсетях за минуты."
        )

        # Устанавливаем полное описание бота (показывается на странице бота)
        await self.bot.set_my_description(
            description=(
                "👋 Добро пожаловать в Loom\n\n"
                "AI SMM инструмент для снижения затрат на рутину.\n\n"
                "Сотрудник говорит голосом:\n"
                "«У нас крутой кейс с клиентом, проект сделали за неделю!»\n\n"
                "Через минуты получаете:\n"
                "✍️ Текст в стиле бренда\n"
                "🎨 Картинку под рубрику\n"
                "📱 Пост для всех соцсетей\n\n"
                "Вместо: ⏱ 2-3 часа работы SMM\n"
                "Получаете: ⚡️ 5 минут на команду\n\n"
                "Нажмите /start чтобы начать!"
            )
        )

    @auto_log()
    @traced_method()
    async def notify_employee_added(
            self,
            body: EmployeeAddedNotificationBody,
    ) -> JSONResponse:
        if body.interserver_secret_key != self.interserver_secret_key:
            self.logger.warning("Не верный межсервисный ключ")
            return JSONResponse(
                content={"status": "error", "message": "Wrong secret token !"},
                status_code=401
            )

        user_state = (await self.state_service.state_by_account_id(
            body.account_id
        ))[0]

        await self.state_service.change_user_state(
            user_state.id,
            organization_id=body.organization_id
        )

        await self.bot.send_message(
            chat_id=user_state.tg_chat_id,
            text=self._format_notification_message(body),
            parse_mode="HTML"
        )

        return JSONResponse(
            content={"status": "ok"},
            status_code=200
        )

    @auto_log()
    @traced_method()
    async def notify_employee_deleted(
            self,
            body: EmployeeDeletedNotificationBody,
    ) -> JSONResponse:
        if body.interserver_secret_key != self.interserver_secret_key:
            self.logger.warning("Не верный межсервисный ключ")
            return JSONResponse(
                content={"status": "error", "message": "Wrong secret token !"},
                status_code=401
            )

        user_state = (await self.state_service.state_by_account_id(
            body.account_id
        ))[0]

        await self.state_service.change_user_state(
            user_state.id,
            organization_id=0
        )

        await self.bot.send_message(
            chat_id=user_state.tg_chat_id,
            text="Вы были удалены из оранизации",
            parse_mode="HTML"
        )

        dialog_manager = self.dialog_bg_factory.bg(
            bot=self.bot,
            user_id=user_state.tg_chat_id,
            chat_id=user_state.tg_chat_id,
        )

        await dialog_manager.start(state=model.IntroStates.intro)

        return JSONResponse(
            content={"status": "ok"},
            status_code=200
        )

    @auto_log()
    @traced_method()
    async def notify_vizard_video_cut_generated(
            self,
            body: NotifyVizardVideoCutGenerated,
    ) -> JSONResponse:
        if body.interserver_secret_key != self.interserver_secret_key:
            self.logger.warning("Не верный межсервисный ключ")
            return JSONResponse(
                content={"status": "error", "message": "Wrong secret token !"},
                status_code=401
            )

        user_state = (await self.state_service.state_by_account_id(
            body.account_id
        ))[0]

        await self.state_service.create_vizard_video_cut_alert(
            state_id=user_state.id,
            youtube_video_reference=body.youtube_video_reference,
            video_count=body.video_count,
        )

        if user_state.can_show_alerts:
            self.logger.info("Показываю алерт о завершении генерации")
            dialog_manager = self.dialog_bg_factory.bg(
                bot=self.bot,
                user_id=user_state.tg_chat_id,
                chat_id=user_state.tg_chat_id,
            )
            await self.state_service.change_user_state(
                user_state.id,
                can_show_alerts=False,
            )
            await dialog_manager.start(
                model.AlertsStates.video_generated_alert,
                mode=StartMode.RESET_STACK,
                show_mode=ShowMode.DELETE_AND_SEND
            )

        return JSONResponse(
            content={"status": "ok"},
            status_code=200
        )

    @auto_log()
    @traced_method()
    async def notify_publication_approved_alert(
            self,
            body: NotifyPublicationApprovedBody,
    ) -> JSONResponse:
        if body.interserver_secret_key != self.interserver_secret_key:
            self.logger.warning("Не верный межсервисный ключ")
            return JSONResponse(
                content={"status": "error", "message": "Wrong secret token !"},
                status_code=401
            )

        user_state = (await self.state_service.state_by_account_id(
            body.account_id
        ))[0]

        await self.state_service.create_publication_approved_alert(
            state_id=user_state.id,
            publication_id=body.publication_id,
        )

        if user_state.can_show_alerts:
            self.logger.info("Показываю алерт о подтверждении публикации")
            dialog_manager = self.dialog_bg_factory.bg(
                bot=self.bot,
                user_id=user_state.tg_chat_id,
                chat_id=user_state.tg_chat_id,
            )
            await self.state_service.change_user_state(
                user_state.id,
                can_show_alerts=False,
            )
            await dialog_manager.start(
                model.AlertsStates.publication_approved_alert,
                mode=StartMode.RESET_STACK,
                show_mode=ShowMode.DELETE_AND_SEND
            )

        return JSONResponse(
            content={"status": "ok"},
            status_code=200
        )

    @auto_log()
    @traced_method()
    async def notify_publication_rejected_alert(
            self,
            body: NotifyPublicationRejectedBody,
    ) -> JSONResponse:
        if body.interserver_secret_key != self.interserver_secret_key:
            self.logger.warning("Не верный межсервисный ключ")
            return JSONResponse(
                content={"status": "error", "message": "Wrong secret token !"},
                status_code=401
            )

        user_state = (await self.state_service.state_by_account_id(
            body.account_id
        ))[0]

        await self.state_service.create_publication_rejected_alert(
            state_id=user_state.id,
            publication_id=body.publication_id,
        )

        if user_state.can_show_alerts:
            self.logger.info("Показываю алерт об отклонении публикации")
            dialog_manager = self.dialog_bg_factory.bg(
                bot=self.bot,
                user_id=user_state.tg_chat_id,
                chat_id=user_state.tg_chat_id,
            )
            await self.state_service.change_user_state(
                user_state.id,
                can_show_alerts=False,
            )
            await dialog_manager.start(
                model.AlertsStates.publication_rejected_alert,
                mode=StartMode.RESET_STACK,
                show_mode=ShowMode.DELETE_AND_SEND
            )

        return JSONResponse(
            content={"status": "ok"},
            status_code=200
        )

    @auto_log()
    @traced_method()
    async def set_cache_file(
            self,
            body: SetCacheFileBody,
    ) -> JSONResponse:
        if body.interserver_secret_key != self.interserver_secret_key:
            self.logger.warning("Не верный межсервисный ключ")
            return JSONResponse(
                content={"status": "error", "message": "Wrong secret token !"},
                status_code=401
            )

        await self.state_service.set_cache_file(
            filename=body.filename,
            file_id=body.file_id
        )

        return JSONResponse(
            content={},
            status_code=200
        )

    def _format_notification_message(self, body: EmployeeAddedNotificationBody) -> str:
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
