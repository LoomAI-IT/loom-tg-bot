from aiogram import Bot
from aiogram.types import Message
from aiogram_dialog import DialogManager

from internal import interface
from internal.dialog.helpers import MessageExtractor

from internal.dialog.brief.helpers import LLMContextManager, TelegramPostFormatter


class LLMChatManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            telegram_client: interface.ITelegramClient,
            loom_content_client: interface.ILoomContentClient,
            create_organization_prompt_generator: interface.ICreateOrganizationPromptGenerator,
            llm_chat_repo: interface.ILLMChatRepo,
    ):
        self.logger = logger
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.telegram_client = telegram_client
        self.loom_content_client = loom_content_client
        self.create_organization_prompt_generator = create_organization_prompt_generator
        self.llm_chat_repo = llm_chat_repo

        self.message_extractor = MessageExtractor(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self.llm_context_manager = LLMContextManager(
            logger=self.logger,
            anthropic_client=self.anthropic_client,
            llm_chat_repo=self.llm_chat_repo,
        )
        self.telegram_post_formatter = TelegramPostFormatter()

    async def process_user_message(
            self,
            dialog_manager: DialogManager,
            message: Message,
            chat_id: int,
    ) -> dict:
        user_text = await self.message_extractor.extract_text_from_message(
            dialog_manager=dialog_manager,
            message=message,
            organization_id=-1
        )

        message_to_llm = f"""
<system>
Оветь обязательно в JSON формате и очень хорошо подумай над тем что тебе сказали в глобальных правилах и в самом stage
HTML разметка должны быть валидной, если есть открывающий тэг, значит должен быть закрывающий, закрывающий не должен существовать без открывающего
ultrathink
</system>

<user>
{user_text}
</user>
"""
        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="user",
            text=f'{{"message_to_llm": {message_to_llm}}}'
        )

        llm_response_json, generate_cost = await self.get_llm_response(
            dialog_manager=dialog_manager,
            chat_id=chat_id
        )

        return llm_response_json

    async def process_telegram_channel(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            telegram_channel_username: str
    ) -> dict:
        telegram_posts = await self.telegram_client.get_channel_posts(
            channel_id=telegram_channel_username,
            limit=50
        )

        posts_text = self.telegram_post_formatter.format_telegram_posts(
            posts=telegram_posts
        )
        message_to_llm = f"""
<system>
{posts_text}
HTML разметка должны быть валидной, если есть открывающий тэг, значит должен быть закрывающий, закрывающий не должен существовать без открывающего
</system>

<user>
Покажи что узнал
</user>
"""
        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="user",
            text=f'{{"message_to_llm": {message_to_llm}}}'
        )

        llm_response_json, generate_cost = await self.get_llm_response(
            dialog_manager=dialog_manager,
            chat_id=chat_id,
            enable_web_search=False
        )

        return llm_response_json

    async def save_llm_response(
            self,
            chat_id: int,
            llm_response_json: dict
    ) -> None:
        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="assistant",
            text=str(llm_response_json)
        )

    async def get_llm_response(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            max_tokens: int = 15000,
            thinking_tokens: int = 10000,
            enable_web_search: bool = True
    ) -> tuple[dict, dict]:
        messages = await self.llm_chat_repo.get_all_messages(chat_id)
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.text
            })

        system_prompt = await self.create_organization_prompt_generator.get_create_organization_system_prompt()
        llm_response_json, generate_cost = await self.anthropic_client.generate_json(
            history=history,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            thinking_tokens=thinking_tokens,
            enable_web_search=enable_web_search,
        )
        self.llm_context_manager.track_tokens(
            dialog_manager=dialog_manager,
            generate_cost=generate_cost
        )

        return llm_response_json, generate_cost
