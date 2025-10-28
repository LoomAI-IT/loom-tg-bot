import traceback

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method

from internal.dialog.helpers import StateManager
from internal.dialog.helpers import MessageExtractor

from internal.dialog.brief.create_organization.helpers import OrganizationManager, LLMChatManager


class CreateOrganizationService(interface.ICreateOrganizationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            telegram_client: interface.ITelegramClient,
            create_organization_prompt_generator: interface.ICreateOrganizationPromptGenerator,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_employee_client: interface.ILoomEmployeeClient,
            loom_content_client: interface.ILoomContentClient,
            llm_chat_repo: interface.ILLMChatRepo,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.telegram_client = telegram_client
        self.create_organization_prompt_generator = create_organization_prompt_generator
        self.loom_organization_client = loom_organization_client
        self.loom_employee_client = loom_employee_client
        self.loom_content_client = loom_content_client
        self.llm_chat_repo = llm_chat_repo
        self.state_repo = state_repo

        # Инициализация приватных сервисов
        self.state_manager = StateManager(
            state_repo=self.state_repo
        )
        self.message_extractor = MessageExtractor(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self._organization_manager = OrganizationManager(
            loom_organization_client=self.loom_organization_client,
            loom_employee_client=self.loom_employee_client,
            state_repo=self.state_repo
        )
        self.llm_chat_manager = LLMChatManager(
            logger=self.logger,
            bot=self.bot,
            anthropic_client=self.anthropic_client,
            telegram_client=self.telegram_client,
            loom_content_client=self.loom_content_client,
            create_organization_prompt_generator=self.create_organization_prompt_generator,
            llm_chat_repo=self.llm_chat_repo,
        )

    @auto_log()
    @traced_method()
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        state = await self.state_manager.get_state(dialog_manager)
        try:
            self.state_manager.set_show_mode(dialog_manager, send=True)

            chat_id = dialog_manager.dialog_data["chat_id"]

            async with tg_action(self.bot, message.chat.id):
                llm_response_json = await self.llm_chat_manager.process_user_message(
                    dialog_manager=dialog_manager,
                    message=message,
                    chat_id=chat_id,
                )

            if llm_response_json.get("telegram_channel_username"):
                telegram_channel_username = llm_response_json["telegram_channel_username"]

                # Сохраняем промежуточный ответ ассистента для правильного кэширования
                await self.llm_chat_manager.save_llm_response(
                    chat_id=chat_id,
                    llm_response_json=llm_response_json
                )

                async with tg_action(self.bot, message.chat.id):
                    llm_response_json = await self.llm_chat_manager.process_telegram_channel(
                        dialog_manager=dialog_manager,
                        chat_id=chat_id,
                        telegram_channel_username=telegram_channel_username
                    )

            if llm_response_json.get("organization_data"):
                organization_data = llm_response_json["organization_data"]

                _ = await self._organization_manager.create_organization_and_admin(
                    state_id=state.id,
                    account_id=state.account_id,
                    organization_data=organization_data
                )

                await dialog_manager.switch_to(state=model.CreateOrganizationStates.organization_created)
                return

            await self.llm_chat_manager.save_llm_response(
                chat_id=chat_id,
                llm_response_json=llm_response_json
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
        dialog_manager.show_mode = ShowMode.EDIT
        await callback.answer()

        await dialog_manager.start(state=model.IntroStates.intro, mode=StartMode.RESET_STACK)

    @auto_log()
    @traced_method()
    async def go_to_create_category(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await callback.answer()

        state = await self.state_manager.get_state(dialog_manager)

        chat = await self.llm_chat_repo.get_chat_by_state_id(state.id)
        if chat:
            await self.llm_chat_repo.delete_chat(chat[0].id)

        await dialog_manager.start(
            state=model.CreateCategoryStates.create_category,
            mode=StartMode.RESET_STACK
        )

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.start(state=model.MainMenuStates.main_menu, mode=StartMode.RESET_STACK)
