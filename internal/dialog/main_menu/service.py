import re
from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.input import MessageInput


from internal import interface, model
from pkg.trace_wrapper import traced_method


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

    @traced_method()
    async def handle_generate_publication_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self.logger.info("Начало обработки ввода промпта для генерации публикации")

        dialog_manager.show_mode = ShowMode.EDIT

        await message.delete()

        dialog_manager.dialog_data.pop("has_void_input_text", None)
        dialog_manager.dialog_data.pop("has_small_input_text", None)
        dialog_manager.dialog_data.pop("has_big_input_text", None)
        dialog_manager.dialog_data.pop("has_invalid_content_type", None)
        dialog_manager.dialog_data.pop("has_empty_voice_text", None)
        dialog_manager.dialog_data.pop("has_small_input_text", None)
        dialog_manager.dialog_data.pop("has_big_input_text", None)

        state = await self._get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        text = await self._speech_to_text(message, dialog_manager, state.organization_id)

        if not text:
            self.logger.info("Пустой текст")
            dialog_manager.dialog_data["has_void_input_text"] = True
            return

        if len(text) < 10:
            self.logger.info("Слишком короткий текст")
            dialog_manager.dialog_data["has_small_input_text"] = True
            return

        if len(text) > 2000:
            self.logger.info("Слишком длинный текст")
            dialog_manager.dialog_data["has_big_input_text"] = True
            return

        dialog_manager.dialog_data["input_text"] = text
        dialog_manager.dialog_data["has_input_text"] = True

        await dialog_manager.switch_to(model.GeneratePublicationStates.generation)
        self.logger.info("Конец обработки ввода промпта для генерации публикации")

    @traced_method()
    async def handle_go_to_content(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
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

        await callback.answer()
        self.logger.info("Завершение перехода к контенту")

    @traced_method()
    async def handle_go_to_organization(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
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

        await callback.answer()
        self.logger.info("Завершение перехода к меню организации")

    @traced_method()
    async def handle_go_to_personal_profile(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
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

        await callback.answer()
        self.logger.info("Завершение перехода к личному профилю")

    async def _speech_to_text(self, message: Message, dialog_manager: DialogManager, organization_id: int) -> str:
        if message.voice:
            file_id = message.voice.file_id
        else:
            file_id = message.audio.file_id

        dialog_manager.dialog_data["voice_transcribe"] = True
        await dialog_manager.show()

        file = await self.bot.get_file(file_id)
        file_data = await self.bot.download_file(file.file_path)

        text = await self.loom_content_client.transcribe_audio(
            organization_id,
            audio_content=file_data.read(),
            audio_filename="audio.mp3",
        )
        dialog_manager.dialog_data["voice_transcribe"] = False
        return text

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
