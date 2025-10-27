from aiogram import Bot
from aiogram.types import Message
from aiogram_dialog import DialogManager

from internal import interface
from internal.dialog._message_extractor import _MessageExtractor
from internal.dialog.brief._llm_context_manager import _LLMContextManager
from internal.dialog.brief._telegram_post_formatter import _TelegramPostFormatter
from internal.dialog.brief.update_category._category_manager import _CategoryManager


class _LLMInteraction:
    def __init__(
            self,
            logger,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            telegram_client: interface.ITelegramClient,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient,
            update_category_prompt_generator: interface.IUpdateCategoryPromptGenerator,
            llm_chat_repo: interface.ILLMChatRepo,
    ):
        self.logger = logger
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.telegram_client = telegram_client
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client
        self.update_category_prompt_generator = update_category_prompt_generator
        self.llm_chat_repo = llm_chat_repo

        # Приватные классы
        self._message_extractor = _MessageExtractor(
            logger=self.logger,
            bot=self.bot,
            loom_content_client=self.loom_content_client
        )
        self.llm_context_manager = _LLMContextManager(
            logger=self.logger,
            anthropic_client=self.anthropic_client,
            llm_chat_repo=self.llm_chat_repo,
        )
        self.category_manager = _CategoryManager(
            loom_content_client=self.loom_content_client,
        )
        self.telegram_post_formatter = _TelegramPostFormatter()

    async def process_user_message(
            self,
            dialog_manager: DialogManager,
            message: Message,
            chat_id: int,
            category_id: int,
            organization_id: int,
    ) -> dict:
        user_text = await self._message_extractor.extract_text_from_message(
            dialog_manager=dialog_manager,
            message=message,
            organization_id=organization_id
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
            chat_id=chat_id,
            category_id=category_id,
            organization_id=organization_id,
        )

        return llm_response_json

    async def process_telegram_channel(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            category_id: int,
            organization_id: int,
            telegram_channel_username: str
    ) -> dict:
        telegram_posts = await self.telegram_client.get_channel_posts(
            channel_id=telegram_channel_username,
            limit=50
        )

        posts_text = self.telegram_post_formatter.format_telegram_posts(posts=telegram_posts)
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

        llm_response_json = await self.get_llm_response(
            dialog_manager=dialog_manager,
            chat_id=chat_id,
            category_id=category_id,
            organization_id=organization_id,
            enable_web_search=False
        )

        return llm_response_json

    async def process_test_generate_publication(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            category_id: int,
            organization_id: int,
            test_category_data: dict,
            user_text_reference: str,
    ) -> tuple[dict, str]:
        test_publication_text = await self.category_manager.test_category_generation(
            test_category_data=test_category_data,
            user_text_reference=user_text_reference,
            organization_id=organization_id,
        )

        message_to_llm = f"""
<system>
[Сгенерированный тестовый пост]
{{
    "test_category": {test_category_data},
    "user_text_reference": {user_text_reference},
    "generated_publication": {test_publication_text},"
}}
Оветь обязательно в JSON формате
HTML разметка должны быть валидной, если есть открывающий тэг, значит должен быть закрывающий, закрывающий не должен существовать без открывающего
</system>

<user>
Вот публикация, показывать ее не надо, подрезюмируй что поменялось, если менялось, если это не первая генерация
</user>
"""
        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="user",
            text=f'{{"message_to_llm": {message_to_llm}}}'
        )

        llm_response_json = await self.get_llm_response(
            dialog_manager=dialog_manager,
            chat_id=chat_id,
            category_id=category_id,
            organization_id=organization_id,
        )

        return llm_response_json, test_publication_text

    async def get_llm_response(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            category_id: int,
            organization_id: int,
            max_tokens: int = 15000,
            thinking_tokens: int = 10000,
            enable_web_search: bool = True
    ) -> dict:
        organization = await self.loom_organization_client.get_organization_by_id(
            organization_id=organization_id
        )
        category = await self.loom_content_client.get_category_by_id(
            category_id=category_id
        )

        messages = await self.llm_chat_repo.get_all_messages(chat_id=chat_id)
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.text
            })

        system_prompt = await self.update_category_prompt_generator.get_update_category_system_prompt(
            organization=organization,
            category=category,
        )
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
