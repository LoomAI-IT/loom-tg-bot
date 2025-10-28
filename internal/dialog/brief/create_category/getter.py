from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method


class CreateCategoryGetter(interface.ICreateCategoryGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            create_category_prompt_generator: interface.ICreateCategoryPromptGenerator,
            llm_chat_repo: interface.ILLMChatRepo,
            state_repo: interface.IStateRepo,
            loom_organization_client: interface.ILoomOrganizationClient
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.create_category_prompt_generator = create_category_prompt_generator
        self.llm_chat_repo = llm_chat_repo
        self.state_repo = state_repo
        self.loom_organization_client = loom_organization_client

    @auto_log()
    @traced_method()
    async def get_create_category_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_state(dialog_manager)

        chat_id = dialog_manager.dialog_data.get("chat_id")
        if not chat_id:
            chat_id = await self.llm_chat_repo.create_chat(state.id)
            dialog_manager.dialog_data["chat_id"] = chat_id

            # Получаем информацию об организации
            organization = await self.loom_organization_client.get_organization_by_id(state.organization_id)

            dialog_manager.dialog_data["total_tokens"] = 0

            user_text = "Привет, помоги мне создать рубрику для контента"
            await self.llm_chat_repo.create_message(
                chat_id=chat_id,
                role="user",
                text=f'{{"message_to_llm": {user_text}}}'
            )
            history = [
                {
                    "role": "user",
                    "content": f'{{"message_to_llm": {user_text}}}',
                }
            ]

            system_prompt = await self.create_category_prompt_generator.get_create_category_system_prompt(organization)
            async with tg_action(self.bot, dialog_manager.event.message.chat.id):
                llm_response_json, _ = await self.anthropic_client.generate_json(
                    history=history,
                    system_prompt=system_prompt,
                    enable_web_search=False,
                    temperature=1,
                    llm_model="claude-sonnet-4-5"
                )

            message_to_user = llm_response_json["message_to_user"]
            await self.llm_chat_repo.create_message(
                chat_id=chat_id,
                role="assistant",
                text=str(llm_response_json)
            )
        else:
            message_to_user = dialog_manager.dialog_data.get("message_to_user")

        data = {
            "message_to_user": message_to_user,
        }

        return data

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
