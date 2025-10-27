from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method

from ._state_helper import _StateHelper
from ._message_extractor import _MessageExtractor
from ._llm_interaction import _LLMInteraction


class UpdateOrganizationService(interface.IUpdateOrganizationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            update_organization_prompt_generator: interface.IUpdateOrganizationPromptGenerator,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient,
            llm_chat_repo: interface.ILLMChatRepo,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.loom_organization_client = loom_organization_client

        # Инициализация приватных сервисов
        self._state_helper = _StateHelper(state_repo)
        self._message_extractor = _MessageExtractor(bot, loom_content_client)
        self._llm_interaction = _LLMInteraction(
            self.logger,
            bot,
            anthropic_client,
            update_organization_prompt_generator,
            loom_organization_client,
            llm_chat_repo
        )

    @auto_log()
    @traced_method()
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_send_mode(dialog_manager)

        state = await self._state_helper.get_state(dialog_manager)
        chat_id = dialog_manager.dialog_data.get("chat_id")

        user_text = await self._message_extractor.extract_text_from_message(message)

        llm_response_json = await self._llm_interaction.process_user_message(
            chat_id=chat_id,
            user_text=user_text,
            organization_id=state.organization_id,
            message=message
        )

        if llm_response_json.get("organization_data"):
            organization_data = llm_response_json["organization_data"]
            dialog_manager.dialog_data["organization_data"] = organization_data

            await self.loom_organization_client.update_organization(
                organization_id=state.organization_id,
                name=organization_data.get("name"),
                description=organization_data.get("description"),
                tone_of_voice=organization_data.get("tone_of_voice"),
                compliance_rules=organization_data.get("compliance_rules"),
                products=organization_data.get("products"),
                locale=organization_data.get("locale"),
                additional_info=organization_data.get("additional_info"),
            )

            await dialog_manager.switch_to(state=model.UpdateOrganizationStates.organization_updated)
            return

        message_to_user = llm_response_json["message_to_user"]
        await self._llm_interaction.save_assistant_message(chat_id, message_to_user)
        dialog_manager.dialog_data["message_to_user"] = message_to_user

    @auto_log()
    @traced_method()
    async def handle_confirm_cancel(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager)
        await callback.answer()

        await dialog_manager.start(state=model.MainMenuStates.main_menu, mode=StartMode.RESET_STACK)

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager)

        await dialog_manager.start(state=model.MainMenuStates.main_menu, mode=StartMode.RESET_STACK)
