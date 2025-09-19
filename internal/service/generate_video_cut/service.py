import re
from typing import Any
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model, common


class GenerateVideoCutDialogService(interface.IGenerateVideoCutDialogService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo,
            kontur_employee_client: interface.IKonturEmployeeClient,
            kontur_content_client: interface.IKonturContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.kontur_employee_client = kontur_employee_client
        self.kontur_content_client = kontur_content_client

    async def get_youtube_input_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "GenerateVideoCutDialogService.get_youtube_input_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Возвращаем пустые данные, так как вся информация статична в диалоге
                data = {}

                self.logger.info(
                    "Данные окна ввода YouTube ссылки загружены",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: self._get_chat_id(dialog_manager),
                    }
                )

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                return {}

    async def handle_youtube_link_input(
            self,
            message: Message,
            message_input: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "GenerateVideoCutDialogService.handle_youtube_link_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                youtube_url = message.text.strip()

                # Валидация YouTube ссылки
                if not self._is_valid_youtube_url(youtube_url):
                    await message.answer(
                        "❌ <b>Неверная ссылка на YouTube</b>\n\n"
                        "Пожалуйста, отправьте корректную ссылку на YouTube видео.\n"
                        "Например: https://www.youtube.com/watch?v=VIDEO_ID",
                        parse_mode="HTML"
                    )
                    return

                # Получаем состояние пользователя
                state = await self._get_state(dialog_manager)

                # Получаем данные сотрудника
                employee = await self.kontur_employee_client.get_employee_by_account_id(
                    state.account_id
                )

                # Запускаем обработку видео асинхронно
                await self.kontur_content_client.generate_video_cut(
                    state.organization_id,
                    state.account_id,
                    youtube_url,
                )

                # Отправляем уведомление о начале обработки
                await message.answer(
                    "⏳ <b>Видео обрабатывается</b>\n\n"
                    "Я создам короткие видео из вашей ссылки.\n"
                    "Это может занять несколько минут.\n\n"
                    "📩 <b>Я уведомлю вас, как только видео будут готовы!</b>\n"
                    "Готовые видео появятся в разделе \"Черновики\" → \"Черновики видео-нарезок\"",
                    parse_mode="HTML"
                )



                # Возвращаем пользователя в главное меню
                await dialog_manager.start(
                    model.MainMenuStates.main_menu,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info(
                    "YouTube ссылка принята к обработке",
                    {
                        common.TELEGRAM_CHAT_ID_KEY: message.chat.id,
                        "youtube_url": youtube_url,
                        "employee_id": employee.id,
                        "organization_id": employee.organization_id,
                    }
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    def _is_valid_youtube_url(self, url: str) -> bool:
        """Проверяет, является ли URL корректной ссылкой на YouTube."""
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(youtube_regex.match(url))

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        """Получить состояние текущего пользователя."""
        chat_id = self._get_chat_id(dialog_manager)
        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]

    def _get_chat_id(self, dialog_manager: DialogManager) -> int:
        """Получить chat_id из dialog_manager."""
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            return dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            return dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")