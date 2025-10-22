from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method


class UpdateCategoryGetter(interface.IUpdateCategoryGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            update_category_prompt_generator: interface.IUpdateCategoryPromptGenerator,
            llm_chat_repo: interface.ILLMChatRepo,
            state_repo: interface.IStateRepo,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.update_category_prompt_generator = update_category_prompt_generator
        self.llm_chat_repo = llm_chat_repo
        self.state_repo = state_repo
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client

    @auto_log()
    @traced_method()
    async def get_select_category_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_state(dialog_manager)

        categories = await self.loom_content_client.get_categories_by_organization(
            state.organization_id
        )

        categories_data = []
        for category in categories:
            categories_data.append({
                "id": category.id,
                "name": category.name,
                "image_style": category.prompt_for_image_style,
            })

        data = {
            "categories": categories_data,
            "has_categories": len(categories_data) > 0,
        }

        return data

    @auto_log()
    @traced_method()
    async def get_update_category_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        state = await self._get_state(dialog_manager)

        category_id = dialog_manager.dialog_data.get("category_id")
        chat_id = dialog_manager.dialog_data.get("chat_id")
        if not chat_id:
            chat_id = await self.llm_chat_repo.create_chat(state.id)
            dialog_manager.dialog_data["chat_id"] = chat_id

            user_text = "Привет, помоги мне обновить мою рубрику"
            await self.llm_chat_repo.create_message(
                chat_id=chat_id,
                role="user",
                text=user_text
            )
            history = [
                {
                    "role": "user",
                    "content": user_text,
                }
            ]
            organization = await self.loom_organization_client.get_organization_by_id(
                state.organization_id,
            )
            category = await self.loom_content_client.get_category_by_id(
                category_id
            )
            system_prompt = await self.update_category_prompt_generator.get_update_category_system_prompt(
                organization,
                category
            )
            async with tg_action(self.bot, dialog_manager.event.message.chat.id):
                llm_response_json, _ = await self.anthropic_client.generate_json(
                    history=history,
                    system_prompt=system_prompt,
                    enable_web_search=False,
                    temperature=1,
                )

            message_to_user = llm_response_json["message_to_user"]
            await self.llm_chat_repo.create_message(
                chat_id=chat_id,
                role="assistant",
                text=message_to_user
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
