import traceback
from contextvars import ContextVar

from aiogram import Bot
from typing import Callable, Any, Awaitable
from aiogram.types import TelegramObject, Update
from aiogram_dialog import StartMode

from internal import interface, common, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class TgMiddleware(interface.ITelegramMiddleware):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_service: interface.IStateService,
            bot: Bot,
            log_context: ContextVar[dict],
    ):
        self.tracer = tel.tracer()
        self.meter = tel.meter()
        self.logger = tel.logger()

        self.state_service = state_service
        self.bot = bot
        self.log_context = log_context
        self.dialog_bg_factory = None

    @traced_method()
    async def logger_middleware01(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: dict[str, Any]
    ):
        message, event_type, message_text, tg_username, tg_chat_id, message_id = self.__extract_metadata(event)

        try:
            user_state = await self.state_service.state_by_id(tg_chat_id)
            if not user_state:
                await self.state_service.create_state(tg_chat_id, tg_username)
                user_state = await self.state_service.state_by_id(tg_chat_id)
            user_state = user_state[0]
        except Exception as e:
            self.logger.error("Ошибка!!!", {"traceback": traceback.format_exc()})
            raise e

        context_token = self.log_context.set({
            common.TELEGRAM_USER_USERNAME_KEY: tg_username,
            common.TELEGRAM_CHAT_ID_KEY: str(tg_chat_id),
            common.TELEGRAM_EVENT_TYPE_KEY: event_type,
            common.ORGANIZATION_ID_KEY: str(user_state.organization_id),
            common.ACCOUNT_ID_KEY: str(user_state.account_id),
        })

        try:
            await handler(event, data)

        except Exception as e:
            if not await self._recovery_start_functionality(tg_chat_id, tg_username):
                raise e

        finally:
            self.log_context.reset(context_token)

    @auto_log()
    @traced_method()
    async def _recovery_start_functionality(self, tg_chat_id: int, tg_username: str):
        user_state = await self.state_service.state_by_id(tg_chat_id)
        if not user_state:
            await self.state_service.create_state(tg_chat_id, tg_username)
            user_state = await self.state_service.state_by_id(tg_chat_id)

        user_state = user_state[0]

        # Создаем dialog_manager для восстановления
        dialog_manager = self.dialog_bg_factory.bg(
            bot=self.bot,
            user_id=tg_chat_id,
            chat_id=tg_chat_id,
        )

        # Определяем состояние для запуска на основе данных пользователя
        if user_state.organization_id == 0 and user_state.account_id == 0:
            target_state = model.IntroStates.user_agreement
            self.logger.info(f"Восстанавливаем в состояние авторизации для пользователя")
        elif user_state.organization_id == 0 and user_state.account_id != 0:
            target_state = model.IntroStates.intro
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
        return True

    def __extract_metadata(self, event: Update):
        if event is None:
            return "", "", "", "", 0, 0

        if event.message is None and event.callback_query is None:
            return "", "", "", "", 0, 0

        message = event.message if event.message is not None else event.callback_query.message
        event_type = "message" if event.message is not None else "callback_query"

        if event_type == "message":
            tg_username = message.from_user.username
        else:
            tg_username = event.callback_query.from_user.username

        tg_username = tg_username if tg_username is not None else "unknown"
        tg_chat_id = message.chat.id
        if message.text is not None:
            message_text = message.text
        else:
            message_text = "Изображение"

        message_id = message.message_id
        return message, event_type, message_text, tg_username, tg_chat_id, message_id
