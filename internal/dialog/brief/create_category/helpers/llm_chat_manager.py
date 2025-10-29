from aiogram import Bot
from aiogram.types import Message
from aiogram_dialog import DialogManager

from internal import interface
from internal.dialog.helpers import MessageExtractor
from internal import model

from internal.dialog.brief.helpers import LLMContextManager, TelegramPostFormatter
from internal.dialog.brief.create_category.helpers import CategoryManager


class LLMChatManager:
    def __init__(
            self,
            logger,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            telegram_client: interface.ITelegramClient,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient,
            create_category_prompt_generator: interface.ICreateCategoryPromptGenerator,
            train_category_prompt_generator: interface.ITrainCategoryPromptGenerator,
            llm_chat_repo: interface.ILLMChatRepo,
    ):
        self.logger = logger
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.telegram_client = telegram_client
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client
        self.create_category_prompt_generator = create_category_prompt_generator
        self.train_category_prompt_generator = train_category_prompt_generator
        self.llm_chat_repo = llm_chat_repo

        # Приватные классы
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
        self.category_manager = CategoryManager(
            loom_content_client=self.loom_content_client,
        )
        self.telegram_post_formatter = TelegramPostFormatter()

    async def process_user_message(
            self,
            dialog_manager: DialogManager,
            message: Message,
            chat_id: int,
            organization_id: int,
            use_train_prompt: bool = False,
            custom_user_text: str = None,
    ) -> dict:
        if custom_user_text:
            user_text = await self.message_extractor.extract_text_from_message(
                dialog_manager=dialog_manager,
                message=message,
                organization_id=organization_id
            )
        else:
            user_text = await self.message_extractor.extract_text_from_message(
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

        llm_response_json = await self.get_llm_response(
            dialog_manager=dialog_manager,
            chat_id=chat_id,
            organization_id=organization_id,
            use_train_prompt=use_train_prompt
        )

        return llm_response_json

    async def process_telegram_channels(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            organization_id: int,
            telegram_channel_username_list: str,
            use_train_prompt: bool = False
    ) -> dict:
        all_telegram_posts = ""
        for telegram_channel_username in telegram_channel_username_list:
            telegram_posts = await self.telegram_client.get_channel_posts(
                channel_id=telegram_channel_username,
                limit=20
            )

            posts_text = self.telegram_post_formatter.format_telegram_posts(posts=telegram_posts)
            all_telegram_posts += posts_text

        message_to_llm = f"""
<system>
{all_telegram_posts}
HTML разметка должны быть валидной, если есть открывающий тэг, значит должен быть закрывающий, закрывающий не должен существовать без открывающего
</system>

<user>
Предложи рубрики
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
            organization_id=organization_id,
            enable_web_search=False,
            use_train_prompt=use_train_prompt
        )

        return llm_response_json

    async def process_test_generate_publication(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            organization_id: int,
            test_category_data: dict,
            user_text_reference: str,
            use_train_prompt: bool = False
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
            organization_id=organization_id,
            use_train_prompt=use_train_prompt
        )

        return llm_response_json, test_publication_text

    async def clear_chat_history(self, dialog_manager: DialogManager, chat_id: int) -> None:
        dialog_manager.dialog_data["total_tokens"] = 0
        await self.llm_chat_repo.delete_all_messages(chat_id=chat_id)

    async def get_llm_response(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            organization_id: int,
            max_tokens: int = 15000,
            thinking_tokens: int = 10000,
            enable_web_search: bool = True,
            use_train_prompt: bool = False
    ) -> dict:
        organization = await self.loom_organization_client.get_organization_by_id(
            organization_id=organization_id
        )

        messages = await self.llm_chat_repo.get_all_messages(chat_id=chat_id)
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.text
            })

        if use_train_prompt:
            category_data = dialog_manager.dialog_data.get("category_data")
            if not category_data:
                raise ValueError("category_data not found in dialog_data")

            category = model.Category(**category_data)
            system_prompt = await self.train_category_prompt_generator.get_train_category_system_prompt(
                organization=organization,
                category=category
            )
        else:
            system_prompt = await self.create_category_prompt_generator.get_create_category_system_prompt(
                organization=organization,
            )

        await self.llm_context_manager.check_and_handle_context_overflow(
            dialog_manager=dialog_manager,
            chat_id=chat_id,
            system_prompt=system_prompt
        )

        llm_response_json, generate_cost = await self.anthropic_client.generate_json(
            history=history,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            thinking_tokens=thinking_tokens,
            enable_web_search=enable_web_search,
            llm_model="claude-haiku-4-5-20251001"
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
