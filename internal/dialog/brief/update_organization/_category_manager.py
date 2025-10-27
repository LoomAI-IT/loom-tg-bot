from aiogram import Bot
from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.tg_action_wrapper import tg_action


class _CategoryUpdater:
    def __init__(
            self,
            logger,
            bot: Bot,
            loom_content_client: interface.ILoomContentClient,
            anthropic_client: interface.IAnthropicClient,
            llm_chat_repo: interface.ILLMChatRepo
    ):
        self.logger = logger
        self.bot = bot
        self.loom_content_client = loom_content_client
        self.anthropic_client = anthropic_client
        self.llm_chat_repo = llm_chat_repo

    async def generate_llm_response(
            self,
            chat_id: int,
            system_prompt: str,
            chat_id_for_action: int
    ) -> tuple[dict, dict]:
        messages = await self.llm_chat_repo.get_all_messages(chat_id)
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.text
            })

        async with tg_action(self.bot, chat_id_for_action):
            llm_response_json, generate_cost = await self.anthropic_client.generate_json(
                history=history,
                system_prompt=system_prompt,
                max_tokens=15000,
                thinking_tokens=10000
            )

        return llm_response_json, generate_cost

    async def analyze_telegram_channel(
            self,
            telegram_channel_username: str,
            chat_id: int,
            telegram_client: interface.ITelegramClient,
            format_telegram_posts_func
    ) -> str:
        """Анализ постов из Telegram канала"""
        telegram_posts = await telegram_client.get_channel_posts(
            telegram_channel_username,
            50
        )

        posts_text = format_telegram_posts_func(telegram_posts)
        message_to_llm = f"""
<system>
{posts_text}
HTML разметка должны быть валидной, если есть открывающий тэг, значит должен быть закрывающий, закрывающий не должен существовать без открывающего
</system>

<user>
Покажи анализ результата
</user>
        """
        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="user",
            text=f'{{"message_to_llm": {message_to_llm}}}'
        )
        return posts_text

    async def test_category_generation(
            self,
            test_category_data: dict,
            user_text_reference: str,
            organization_id: int,
            chat_id: int,
            tg_chat_id: int,
            parse_mode: str
    ) -> str:
        """Тестовая генерация публикации для категории"""
        async with tg_action(self.bot, tg_chat_id):
            test_publication_text = await self.loom_content_client.test_generate_publication(
                user_text_reference=user_text_reference,
                organization_id=organization_id,
                name=test_category_data.get("name", ""),
                hint=test_category_data.get("hint", ""),
                goal=test_category_data.get("goal", ""),
                tone_of_voice=test_category_data.get("tone_of_voice", []),
                brand_rules=test_category_data.get("brand_rules", []),
                creativity_level=test_category_data.get("creativity_level", 5),
                audience_segment=test_category_data.get("audience_segment", ""),
                len_min=test_category_data.get("len_min", 200),
                len_max=test_category_data.get("len_max", 400),
                n_hashtags_min=test_category_data.get("n_hashtags_min", 1),
                n_hashtags_max=test_category_data.get("n_hashtags_max", 2),
                cta_type=test_category_data.get("cta_type", ""),
                cta_strategy=test_category_data.get("cta_strategy", {}),
                good_samples=test_category_data.get("good_samples", []),
                bad_samples=test_category_data.get("bad_samples", []),
                additional_info=test_category_data.get("additional_info", []),
                prompt_for_image_style=test_category_data.get("prompt_for_image_style", ""),
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

        await self.bot.send_message(
            chat_id=tg_chat_id,
            text="Ваша публикация:<br><br>" + test_publication_text,
            parse_mode=parse_mode
        )

        return test_publication_text

    async def update_category(
            self,
            category_id: int,
            category_data: dict
    ) -> None:
        """Обновление категории"""
        await self.loom_content_client.update_category(
            category_id=category_id,
            name=category_data.get("name"),
            goal=category_data.get("goal"),
            tone_of_voice=category_data.get("tone_of_voice"),
            brand_rules=category_data.get("brand_rules"),
            creativity_level=category_data.get("creativity_level"),
            audience_segment=category_data.get("audience_segment"),
            len_min=category_data.get("len_min"),
            len_max=category_data.get("len_max"),
            n_hashtags_min=category_data.get("n_hashtags_min"),
            n_hashtags_max=category_data.get("n_hashtags_max"),
            cta_type=category_data.get("cta_type"),
            cta_strategy=category_data.get("cta_strategy"),
            good_samples=category_data.get("good_samples"),
            bad_samples=category_data.get("bad_samples"),
            additional_info=category_data.get("additional_info"),
            prompt_for_image_style=category_data.get("prompt_for_image_style"),
        )
