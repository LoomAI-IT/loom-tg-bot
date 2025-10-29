import traceback

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager
from internal.dialog.brief.helpers import LLMContextManager
from internal.dialog.brief.create_category.helpers import CategoryManager, LLMChatManager


class CreateCategoryService(interface.ICreateCategoryService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            telegram_client: interface.ITelegramClient,
            create_category_prompt_generator: interface.ICreateCategoryPromptGenerator,
            train_category_prompt_generator: interface.ITrainCategoryPromptGenerator,
            llm_chat_repo: interface.ILLMChatRepo,
            state_repo: interface.IStateRepo,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.telegram_client = telegram_client
        self.create_category_prompt_generator = create_category_prompt_generator
        self.train_category_prompt_generator = train_category_prompt_generator
        self.llm_chat_repo = llm_chat_repo
        self.state_repo = state_repo
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client

        # Инициализация приватных сервисов
        self.state_manager = StateManager(
            self.state_repo
        )

        self.llm_context_manager = LLMContextManager(
            self.logger,
            self.anthropic_client,
            self.llm_chat_repo
        )
        self.category_manager = CategoryManager(
            self.loom_content_client,
        )
        self.llm_chat_manager = LLMChatManager(
            self.logger,
            self.bot,
            self.anthropic_client,
            self.telegram_client,
            self.loom_organization_client,
            self.loom_content_client,
            self.create_category_prompt_generator,
            self.train_category_prompt_generator,
            self.llm_chat_repo,
        )

    @auto_log()
    @traced_method()
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        state = await self.state_manager.get_state(dialog_manager=dialog_manager)
        try:
            self.state_manager.set_show_mode(dialog_manager, send=True)

            chat_id = dialog_manager.dialog_data.get("chat_id")
            use_train_prompt = dialog_manager.dialog_data.get("category_data") is not None

            async with tg_action(self.bot, message.chat.id):
                llm_response_json = await self.llm_chat_manager.process_user_message(
                    dialog_manager=dialog_manager,
                    message=message,
                    chat_id=chat_id,
                    organization_id=state.organization_id,
                    use_train_prompt=use_train_prompt
                )
            current_stage = llm_response_json.get("current_stage")

            if llm_response_json.get("telegram_channel_username_list") and current_stage == "3":
                telegram_channel_username_list = llm_response_json["telegram_channel_username_list"]

                await self.llm_chat_manager.save_llm_response(
                    chat_id=chat_id,
                    llm_response_json=llm_response_json,
                )

                async with tg_action(self.bot, message.chat.id):
                    llm_response_json = await self.llm_chat_manager.process_telegram_channels(
                        dialog_manager=dialog_manager,
                        chat_id=chat_id,
                        organization_id=state.organization_id,
                        telegram_channel_username_list=telegram_channel_username_list,
                        use_train_prompt=use_train_prompt
                    )

            if llm_response_json.get("test_category") and llm_response_json.get("user_text_reference"):
                test_category_data = llm_response_json["test_category"]
                user_text_reference = llm_response_json["user_text_reference"]

                await self.llm_chat_manager.save_llm_response(
                    chat_id=chat_id,
                    llm_response_json=llm_response_json,
                )

                async with tg_action(self.bot, message.chat.id):
                    llm_response_json, test_publication_text = await self.llm_chat_manager.process_test_generate_publication(
                        dialog_manager=dialog_manager,
                        chat_id=chat_id,
                        organization_id=state.organization_id,
                        test_category_data=test_category_data,
                        user_text_reference=user_text_reference,
                        use_train_prompt=use_train_prompt
                    )

                await self.bot.send_message(
                    chat_id=state.tg_chat_id,
                    text="<b>Ваша публикация:</b><br><br>" + test_publication_text,
                    parse_mode=SULGUK_PARSE_MODE
                )

            if llm_response_json.get("category_data"):
                category_data = llm_response_json["category_data"]
                await self.category_manager.save_category(
                    dialog_manager=dialog_manager,
                    organization_id=state.organization_id,
                    category_data=category_data
                )

                await self.llm_chat_manager.clear_chat_history(
                    dialog_manager=dialog_manager,
                    chat_id=chat_id
                )

                llm_response_json = await self.llm_chat_manager.process_user_message(
                    dialog_manager=dialog_manager,
                    message=message,
                    chat_id=chat_id,
                    organization_id=state.organization_id,
                    use_train_prompt=True,
                    custom_user_text="<system>Финальный этап -- обучение</system>"
                )

            if llm_response_json.get("final_category"):
                final_category = llm_response_json["final_category"]

                category_id = await self.category_manager.create_category(
                    organization_id=state.organization_id,
                    category_data=final_category
                )

                dialog_manager.dialog_data["category_id"] = category_id
                await dialog_manager.switch_to(state=model.CreateCategoryStates.category_created)
                return

            await self.llm_chat_manager.save_llm_response(
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
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)
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
        self.state_manager.set_show_mode(dialog_manager=dialog_manager, edit=True)

        await dialog_manager.start(state=model.MainMenuStates.main_menu, mode=StartMode.RESET_STACK)
