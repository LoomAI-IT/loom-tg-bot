import traceback
from typing import Any

from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method

from internal.dialog._state_helper import _StateHelper
from internal.dialog.brief._llm_context_manager import _LLMContextManager
from ._category_manager import _CategoryManager
from ._llm_interaction import _LLMInteraction


class UpdateCategoryService(interface.IUpdateCategoryService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            update_category_prompt_generator: interface.IUpdateCategoryPromptGenerator,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient,
            telegram_client: interface.ITelegramClient,
            llm_chat_repo: interface.ILLMChatRepo,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.update_category_prompt_generator = update_category_prompt_generator
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client
        self.telegram_client = telegram_client
        self.llm_chat_repo = llm_chat_repo
        self.state_repo = state_repo

        # Инициализация приватных сервисов
        self._state_helper = _StateHelper(
            self.state_repo
        )

        self._llm_context_manager = _LLMContextManager(
            self.logger,
            self.anthropic_client,
            self.llm_chat_repo
        )
        self._category_manger = _CategoryManager(
            self.loom_content_client,
        )
        self._llm_interaction = _LLMInteraction(
            self.logger,
            self.bot,
            self.anthropic_client,
            self.telegram_client,
            self.loom_organization_client,
            self.loom_content_client,
            self.update_category_prompt_generator,
            self.llm_chat_repo,
        )

    @auto_log()
    @traced_method()
    async def handle_select_category(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            category_id: str
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager)
        await callback.answer()

        category = await self.loom_content_client.get_category_by_id(
            int(category_id)
        )

        dialog_manager.dialog_data["category_id"] = category.id
        dialog_manager.dialog_data["category_name"] = category.name

        await dialog_manager.switch_to(state=model.UpdateCategoryStates.update_category)

    @auto_log()
    @traced_method()
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        state = await self._state_helper.get_state(dialog_manager)
        try:
            self._state_helper.set_edit_mode(dialog_manager)

            category_id = dialog_manager.dialog_data.get("category_id")
            chat_id = dialog_manager.dialog_data.get("chat_id")

            async with tg_action(self.bot, message.chat.id):
                llm_response_json = await self._llm_interaction.process_user_message(
                    dialog_manager=dialog_manager,
                    message=message,
                    chat_id=chat_id,
                    category_id=category_id,
                    organization_id=state.organization_id,
                )

            if llm_response_json.get("telegram_channel_username_list"):
                telegram_channel_username_list = llm_response_json["telegram_channel_username_list"]

                for telegram_channel_username in telegram_channel_username_list:
                    async with tg_action(self.bot, message.chat.id):
                        llm_response_json, generate_cost = await self._llm_interaction.process_telegram_channel(
                            dialog_manager=dialog_manager,
                            chat_id=chat_id,
                            category_id=category_id,
                            organization_id=state.organization_id,
                            telegram_channel_username=telegram_channel_username,
                        )

            if llm_response_json.get("test_category") and llm_response_json.get("user_text_reference"):
                test_category_data = llm_response_json["test_category"]
                user_text_reference = llm_response_json["user_text_reference"]

                async with tg_action(self.bot, message.chat.id):
                    llm_response_json, test_publication_text = await self._llm_interaction.process_test_generate_publication(
                        dialog_manager=dialog_manager,
                        chat_id=chat_id,
                        category_id=category_id,
                        organization_id=state.organization_id,
                        test_category_data=test_category_data,
                        user_text_reference=user_text_reference,
                    )

                await self.bot.send_message(
                    chat_id=state.tg_chat_id,
                    text="Ваша публикация:<br><br>" + test_publication_text,
                    parse_mode=SULGUK_PARSE_MODE
                )

            if llm_response_json.get("final_category"):
                category_data = llm_response_json["final_category"]
                await self._category_manger.update_category(
                    category_id=category_id,
                    category_data=category_data
                )

                await dialog_manager.switch_to(state=model.UpdateCategoryStates.category_updated)
                return

            await self._llm_interaction.save_llm_response(
                chat_id=chat_id,
                llm_response_json=llm_response_json,
            )
            dialog_manager.dialog_data["message_to_user"] = llm_response_json["message_to_user"]

        except Exception as e:
            await self.bot.send_message(
                state.tg_chat_id,
                "Произошла непредвиденная ошибка, попробуйте продолжить диалог"
            )
            self.logger.error("Ошибка!!!", {"traceback": traceback.format_exc()})

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
