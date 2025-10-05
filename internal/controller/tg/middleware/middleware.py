import time
import traceback
from contextvars import ContextVar

from aiogram import Bot
from typing import Callable, Any, Awaitable
from aiogram.types import TelegramObject, Update
from aiogram.exceptions import TelegramBadRequest
from aiogram_dialog import StartMode, BgManagerFactory
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, common, model


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

    async def logger_middleware01(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: dict[str, Any]
    ):
        with self.tracer.start_as_current_span(
                "TgMiddleware.logger_middleware03",
                kind=SpanKind.INTERNAL
        ) as span:
            start_time = time.time()

            message, event_type, message_text, tg_username, tg_chat_id, message_id = self.__extract_metadata(event)

            try:
                user_state = await self.state_service.state_by_id(tg_chat_id)
                if not user_state:
                    await self.state_service.create_state(tg_chat_id, tg_username)
                    user_state = await self.state_service.state_by_id(tg_chat_id)
                user_state = user_state[0]

                context_token = self.log_context.set({
                    common.TELEGRAM_USER_USERNAME_KEY: tg_username,
                    common.TELEGRAM_CHAT_ID_KEY: str(tg_chat_id),
                    common.TELEGRAM_EVENT_TYPE_KEY: event_type,
                    common.ORGANIZATION_ID_KEY: str(user_state.organization_id),
                    common.ACCOUNT_ID_KEY: str(user_state.account_id),
                })

                self.logger.info(f"Начали обработку telegram {event_type}")

                await handler(event, data)

                self.logger.info(f"Закончили обработку telegram {event_type}", {
                    common.TELEGRAM_MESSAGE_DURATION_KEY: int((time.time() - start_time) * 1000),
                })

                span.set_status(Status(StatusCode.OK))

            except TelegramBadRequest as err:
                self.logger.warning("TelegramBadRequest в tg middleware")
                pass

            except Exception as err:
                self.logger.error(f"Ошибка обработки telegram {event_type}", {
                    common.TELEGRAM_MESSAGE_DURATION_KEY: int((time.time() - start_time) * 1000),
                    common.TRACEBACK_KEY: traceback.format_exc()
                })
                await self._recovery_start_functionality(tg_chat_id, tg_username)

                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

            finally:
                self.log_context.reset(context_token)

    async def _recovery_start_functionality(self, tg_chat_id: int, tg_username: str):
        with self.tracer.start_as_current_span(
                "TgMiddleware._recovery_start_functionality",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info(f"Начинаем восстановление пользователя через функционал /start", )

                # Получаем или создаем состояние пользователя
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
                    f"Пользователь {tg_chat_id} успешно восстановлен в состояние {target_state}",
                    {common.TELEGRAM_CHAT_ID_KEY: tg_chat_id}
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as recovery_err:
                self.logger.error(
                    f"Критическая ошибка при восстановлении пользователя {tg_chat_id}",
                    {
                        common.ERROR_KEY: str(recovery_err),
                        common.TRACEBACK_KEY: traceback.format_exc(),
                        common.TELEGRAM_CHAT_ID_KEY: tg_chat_id,
                    }
                )

                (recovery_err)
                span.set_status(Status(StatusCode.ERROR, str(recovery_err)))

                # Последняя попытка - отправить пользователю сообщение с инструкцией
                try:
                    await self.bot.send_message(
                        chat_id=tg_chat_id,
                        text="❌ Произошла критическая ошибка. Пожалуйста, отправьте команду /start для восстановления работы."
                    )
                except Exception as msg_err:
                    self.logger.error(
                        f"Не удалось отправить сообщение о восстановлении пользователю {tg_chat_id}",
                        {
                            common.ERROR_KEY: str(msg_err),
                            common.TELEGRAM_CHAT_ID_KEY: tg_chat_id,
                        }
                    )

    def __extract_metadata(self, event: Update):
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