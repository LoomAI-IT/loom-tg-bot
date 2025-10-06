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

    @auto_log()
    @traced_method()
    async def notify_employee_added(
            self,
            body: EmployeeNotificationBody,
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
            dialog_manager = self.dialog_bg_factory.bg(
                bot=self.bot,
                user_id=user_state.tg_chat_id,
                chat_id=user_state.tg_chat_id,
            )
            await dialog_manager.start(
                model.GenerateVideoCutStates.video_generated_alert,
                mode=StartMode.RESET_STACK,
                show_mode=ShowMode.EDIT
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

    def _get_chat_id(self, telegram_update: Update) -> int:
        """Извлекает chat_id из Telegram Update"""
        if telegram_update.message:
            return telegram_update.message.chat.id
        elif telegram_update.callback_query and telegram_update.callback_query.message:
            return telegram_update.callback_query.message.chat.id
        else:
            raise ValueError("Не удалось извлечь chat_id из Update")

    async def _recovery_start_functionality(self, chat_id: int, tg_username: str):
        """Восстанавливает функциональность пользователя через /start"""
        try:
            self.logger.info(f"Начинаем восстановление пользователя через функционал /start")

            # Получаем или создаем состояние пользователя
            user_state = await self.state_service.state_by_id(chat_id)
            if not user_state:
                await self.state_service.create_state(chat_id, tg_username)
                user_state = await self.state_service.state_by_id(chat_id)

            user_state = user_state[0]



            # Создаем dialog_manager для восстановления
            dialog_manager = self.dialog_bg_factory.bg(
                bot=self.bot,
                user_id=chat_id,
                chat_id=chat_id,
            )

            # Определяем состояние для запуска на основе данных пользователя
            if user_state.organization_id == 0 and user_state.account_id == 0:
                target_state = model.AuthStates.user_agreement
                self.logger.info(f"Восстанавливаем в состояние авторизации для пользователя")
            elif user_state.organization_id == 0 and user_state.account_id != 0:
                target_state = model.AuthStates.access_denied
                self.logger.info(f"Восстанавливаем в состояние отказа доступа для пользователя")
            else:
                target_state = model.MainMenuStates.main_menu
                self.logger.info(f"Восстанавливаем в главное меню для пользователя")

            # Запускаем соответствующий диалог
            await dialog_manager.start(
                target_state,
                mode=StartMode.RESET_STACK
            )

            # Восстанавливаем флаг показа уведомлений
            await self.state_service.change_user_state(
                state_id=user_state.id,
                can_show_alerts=True
            )

            self.logger.info(
                f"Пользователь {chat_id} успешно восстановлен в состояние {target_state}",
                {"tg_chat_id": chat_id}
            )

        except Exception as recovery_err:
            self.logger.error(
                f"Критическая ошибка при восстановлении пользователя {chat_id}",
                {
                    "error": str(recovery_err),
                    "traceback": traceback.format_exc(),
                    "tg_chat_id": chat_id,
                }
            )

            # Последняя попытка - отправить пользователю сообщение с инструкцией
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Произошла критическая ошибка. Пожалуйста, отправьте команду /start для восстановления работы."
                )
            except Exception as msg_err:
                self.logger.error(
                    f"Не удалось отправить сообщение о восстановлении пользователю {chat_id}",
                    {
                        "error": str(msg_err),
                        "tg_chat_id": chat_id,
                    }
                )
