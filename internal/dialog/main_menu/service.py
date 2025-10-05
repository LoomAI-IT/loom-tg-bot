import re
from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.input import MessageInput

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class MainMenuService(interface.IMainMenuService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            state_repo: interface.IStateRepo,
            loom_content_client: interface.ILoomContentClient
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo
        self.bot = bot
        self.loom_content_client = loom_content_client

    async def handle_text_input(
            self,
            message: Message,
            widget: Any,
            dialog_manager: DialogManager,
            text: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuService.handle_text_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки текстового ввода")

                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_invalid_voice_type", None)
                dialog_manager.dialog_data.pop("has_long_voice_duration", None)
                dialog_manager.dialog_data.pop("has_empty_voice_text", None)
                dialog_manager.dialog_data.pop("has_small_input_text", None)
                dialog_manager.dialog_data.pop("has_big_input_text", None)
                dialog_manager.dialog_data.pop("has_void_input_text", None)
                dialog_manager.dialog_data.pop("has_small_input_text", None)
                dialog_manager.dialog_data.pop("has_big_input_text", None)

                if text.startswith("http"):
                    self.logger.info("Обнаружена ссылка в тексте")
                    if not self._is_valid_youtube_url(text):
                        self.logger.info("Ссылка не прошла валидацию YouTube")
                        dialog_manager.dialog_data["has_invalid_youtube_url"] = True
                        return

                    self.logger.info("Запуск обработки YouTube видео")
                    dialog_manager.dialog_data["is_processing_video"] = True

                    state = await self._get_state(dialog_manager)
                    await self.loom_content_client.generate_video_cut(
                        state.organization_id,
                        state.account_id,
                        text,
                    )

                    await dialog_manager.start(
                        model.GenerateVideoCutStates.input_youtube_link,
                        data=dialog_manager.dialog_data,
                    )
                    return

                text = text.strip()
                if not text:
                    self.logger.info("Текст пустой после очистки")
                    dialog_manager.dialog_data["has_void_input_text"] = True
                    return

                if len(text) < 10:
                    self.logger.info("Текст слишком короткий")
                    dialog_manager.dialog_data["has_small_input_text"] = True
                    return

                if len(text) > 2000:
                    self.logger.info("Текст слишком длинный")
                    dialog_manager.dialog_data["has_big_input_text"] = True
                    return

                dialog_manager.dialog_data["input_text"] = text
                dialog_manager.dialog_data["has_input_text"] = True

                self.logger.info("Текст принят для генерации")

                await dialog_manager.start(
                    model.GeneratePublicationStates.select_category,
                    data=dialog_manager.dialog_data,
                )

                self.logger.info("Завершение обработки текстового ввода")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_voice_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuService.handle_voice_input",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало обработки голосового ввода")

                dialog_manager.show_mode = ShowMode.EDIT

                await message.delete()

                dialog_manager.dialog_data.pop("has_void_input_text", None)
                dialog_manager.dialog_data.pop("has_small_input_text", None)
                dialog_manager.dialog_data.pop("has_big_input_text", None)
                dialog_manager.dialog_data.pop("has_invalid_voice_type", None)
                dialog_manager.dialog_data.pop("has_long_voice_duration", None)
                dialog_manager.dialog_data.pop("has_empty_voice_text", None)
                dialog_manager.dialog_data.pop("has_small_input_text", None)
                dialog_manager.dialog_data.pop("has_big_input_text", None)

                state = await self._get_state(dialog_manager)

                if message.content_type not in [ContentType.VOICE, ContentType.AUDIO]:
                    self.logger.info("Неверный тип голосового сообщения")
                    dialog_manager.dialog_data["has_invalid_voice_type"] = True
                    return

                if message.voice:
                    file_id = message.voice.file_id
                    duration = message.voice.duration
                else:
                    file_id = message.audio.file_id
                    duration = message.audio.duration

                if duration > 300:
                    self.logger.info("Голосовое сообщение слишком длинное")
                    dialog_manager.dialog_data["has_long_voice_duration"] = True
                    return

                dialog_manager.dialog_data["voice_transcribe"] = True
                await dialog_manager.show()

                file = await self.bot.get_file(file_id)
                file_data = await self.bot.download_file(file.file_path)

                text = await self.loom_content_client.transcribe_audio(
                    state.organization_id,
                    audio_content=file_data.read(),
                    audio_filename="audio.mp3",
                )

                if not text or not text.strip():
                    self.logger.info("Голосовое сообщение не содержит текста")
                    dialog_manager.dialog_data["has_empty_voice_text"] = True
                    return

                text = text.strip()

                if len(text) < 10:
                    self.logger.info("Распознанный текст слишком короткий")
                    dialog_manager.dialog_data["has_small_input_text"] = True
                    return

                if len(text) > 2000:
                    self.logger.info("Распознанный текст слишком длинный")
                    dialog_manager.dialog_data["has_big_input_text"] = True
                    return

                dialog_manager.dialog_data["input_text"] = text
                dialog_manager.dialog_data["has_input_text"] = True
                dialog_manager.dialog_data["voice_transcribe"] = False

                self.logger.info("Голосовое сообщение успешно обработано")
                await dialog_manager.start(
                    model.GeneratePublicationStates.select_category,
                    data=dialog_manager.dialog_data,
                )

                self.logger.info("Завершение обработки голосового ввода")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_content(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuService.handle_go_to_content",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало перехода к контенту")

                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    show_error_recovery=False
                )

                await dialog_manager.start(
                    model.ContentMenuStates.content_menu,
                    mode=StartMode.RESET_STACK
                )

                await callback.answer("📂 Открываю мой контент")

                self.logger.info("Завершение перехода к контенту")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_organization(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuService.handle_go_to_organization",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало перехода к меню организации")

                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    show_error_recovery=False
                )

                await dialog_manager.start(
                    model.OrganizationMenuStates.organization_menu,
                    mode=StartMode.RESET_STACK
                )

                await callback.answer("🏢 Открываю настройки организации")

                self.logger.info("Завершение перехода к меню организации")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def handle_go_to_personal_profile(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuService.handle_go_to_personal_profile",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info("Начало перехода к личному профилю")

                state = await self._get_state(dialog_manager)
                await self.state_repo.change_user_state(
                    state_id=state.id,
                    show_error_recovery=False
                )

                await dialog_manager.start(
                    model.PersonalProfileStates.personal_profile,
                    mode=StartMode.RESET_STACK
                )

                await callback.answer("👤 Открываю личный профиль")

                self.logger.info("Завершение перехода к личному профилю")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    def _is_valid_youtube_url(self, url: str) -> bool:
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(youtube_regex.match(url))

    async def _get_state(self, dialog_manager: DialogManager) -> model.UserState:
        if hasattr(dialog_manager.event, 'message') and dialog_manager.event.message:
            chat_id = dialog_manager.event.message.chat.id
        elif hasattr(dialog_manager.event, 'chat'):
            chat_id = dialog_manager.event.chat.id
        else:
            raise ValueError("Cannot extract chat_id from dialog_manager")

        state = await self.state_repo.state_by_id(chat_id)
        if not state:
            raise ValueError(f"State not found for chat_id: {chat_id}")
        return state[0]