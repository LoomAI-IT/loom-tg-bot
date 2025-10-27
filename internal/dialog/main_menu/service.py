from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method

from internal.dialog._state_helper import _StateHelper
from internal.dialog._message_extractor import _MessageExtractor
from ._error_flags import _ErrorFlagsManager
from ._navigation import _NavigationManager
from ._validation import _ValidationService


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

        # Инициализация приватных сервисов
        self._state_helper = _StateHelper(state_repo)
        self._error_flags = _ErrorFlagsManager()
        self._validation = _ValidationService(self.logger)
        self._message_extractor = _MessageExtractor(self.logger, bot, loom_content_client)
        self._navigation = _NavigationManager(state_repo)

    @auto_log()
    @traced_method()
    async def handle_generate_publication_prompt_input(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager)

        await message.delete()

        self._error_flags.clear_input_error_flags(dialog_manager)

        state = await self._state_helper.get_state(dialog_manager)

        if message.content_type not in [ContentType.VOICE, ContentType.AUDIO, ContentType.TEXT]:
            self.logger.info("Неверный тип контента")
            dialog_manager.dialog_data["has_invalid_content_type"] = True
            return

        text = await self._message_extractor.process_voice_or_text_input(
            message, dialog_manager, state.organization_id
        )

        if not self._validation.validate_input_text(text, dialog_manager):
            return

        dialog_manager.dialog_data["input_text"] = text
        dialog_manager.dialog_data["has_input_text"] = True

        await dialog_manager.start(
            model.GeneratePublicationStates.select_category,
            data=dialog_manager.dialog_data,
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_content(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        state = await self._state_helper.get_state(dialog_manager)
        await self._navigation.navigate_to_content(callback, dialog_manager, state)

    @auto_log()
    @traced_method()
    async def handle_go_to_organization(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        state = await self._state_helper.get_state(dialog_manager)
        await self._navigation.navigate_to_organization(callback, dialog_manager, state)

    @auto_log()
    @traced_method()
    async def handle_go_to_personal_profile(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        state = await self._state_helper.get_state(dialog_manager)
        await self._navigation.navigate_to_personal_profile(callback, dialog_manager, state)
