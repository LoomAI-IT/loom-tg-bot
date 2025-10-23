import traceback

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method


class CreateCategoryService(interface.ICreateCategoryService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            telegram_client: interface.ITelegramClient,
            create_category_prompt_generator: interface.ICreateCategoryPromptGenerator,
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
        self.llm_chat_repo = llm_chat_repo
        self.state_repo = state_repo
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client
        self.CONTEXT_TOKEN_THRESHOLD = 30000

    @auto_log()
    @traced_method()
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        state = await self._get_state(dialog_manager)
        try:
            dialog_manager.show_mode = ShowMode.SEND

            user_text = await self._extract_text_from_message(message)
            if not user_text:
                dialog_manager.show_mode = ShowMode.NO_UPDATE
                return

            organization = await self.loom_organization_client.get_organization_by_id(state.organization_id)

            chat_id = dialog_manager.dialog_data.get("chat_id")
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

            system_prompt = await self.create_category_prompt_generator.get_create_category_system_prompt(organization)

            await self._check_and_handle_context_overflow(dialog_manager, chat_id, system_prompt)

            messages = await self.llm_chat_repo.get_all_messages(chat_id)
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.text
                })

            async with tg_action(self.bot, message.chat.id):
                llm_response_json, generate_cost = await self.anthropic_client.generate_json(
                    history=history,
                    system_prompt=system_prompt,
                    max_tokens=15000,
                    thinking_tokens=10000
                )

            self._track_tokens(dialog_manager, generate_cost)

            if llm_response_json.get("telegram_channel_username"):
                telegram_channel_username = llm_response_json.get("telegram_channel_username")
                telegram_posts = await self.telegram_client.get_channel_posts(
                    telegram_channel_username,
                    10
                )

                posts_text = self._format_telegram_posts(telegram_posts)
                message_to_llm = f"""
<system>
{posts_text}
</system>
"""
                await self.llm_chat_repo.create_message(
                    chat_id=chat_id,
                    role="user",
                    text=f'{{"message_to_llm": {message_to_llm}}}'
                )

                await self._check_and_handle_context_overflow(dialog_manager, chat_id, system_prompt)

                messages = await self.llm_chat_repo.get_all_messages(chat_id)
                history = []
                for msg in messages:
                    history.append({
                        "role": msg.role,
                        "content": msg.text
                    })

                async with tg_action(self.bot, message.chat.id):
                    llm_response_json, generate_cost = await self.anthropic_client.generate_json(
                        history=history,
                        system_prompt=system_prompt,
                        max_tokens=15000,
                        enable_web_search=False,
                        thinking_tokens=10000
                    )

                self._track_tokens(dialog_manager, generate_cost)

            if llm_response_json.get("test_category") and llm_response_json.get("user_text_reference"):
                test_category_data = llm_response_json["test_category"]
                user_text_reference = llm_response_json["user_text_reference"]

                async with tg_action(self.bot, message.chat.id):
                    test_publication_text = await self.loom_content_client.test_generate_publication(
                        user_text_reference=user_text_reference,
                        organization_id=state.organization_id,
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

                await self._check_and_handle_context_overflow(dialog_manager, chat_id, system_prompt)

                messages = await self.llm_chat_repo.get_all_messages(chat_id)
                history = []
                for msg in messages:
                    history.append({
                        "role": msg.role,
                        "content": msg.text
                    })

                async with tg_action(self.bot, message.chat.id):
                    llm_response_json, generate_cost = await self.anthropic_client.generate_json(
                        history=history,
                        system_prompt=system_prompt,
                        max_tokens=15000,
                        enable_web_search=False,
                        thinking_tokens=10000
                    )

                # Отслеживаем токены после вызова LLM
                self._track_tokens(dialog_manager, generate_cost)

                await self.bot.send_message(
                    chat_id=state.tg_chat_id,
                    text="Ваша публикация:<br><br>" + test_publication_text,
                    parse_mode=SULGUK_PARSE_MODE
                )

            if llm_response_json.get("final_category"):
                category_data = llm_response_json["final_category"]
                dialog_manager.dialog_data["category_data"] = category_data

                category_id = await self.loom_content_client.create_category(
                    organization_id=state.organization_id,
                    name=category_data.get("name", ""),
                    hint=category_data.get("hint", ""),
                    goal=category_data.get("goal", ""),
                    tone_of_voice=category_data.get("tone_of_voice", []),
                    brand_rules=category_data.get("brand_rules", []),
                    creativity_level=category_data.get("creativity_level", 5),
                    audience_segment=category_data.get("audience_segment", ""),
                    len_min=category_data.get("len_min", 200),
                    len_max=category_data.get("len_max", 400),
                    n_hashtags_min=category_data.get("n_hashtags_min", 1),
                    n_hashtags_max=category_data.get("n_hashtags_max", 2),
                    cta_type=category_data.get("cta_type", ""),
                    cta_strategy=category_data.get("cta_strategy", {}),
                    good_samples=category_data.get("good_samples", []),
                    bad_samples=category_data.get("bad_samples", []),
                    additional_info=category_data.get("additional_info", []),
                    prompt_for_image_style=category_data.get("prompt_for_image_style", ""),
                )

                dialog_manager.dialog_data["category_id"] = category_id
                await dialog_manager.switch_to(model.CreateCategoryStates.category_created)
                return

            message_to_user = llm_response_json["message_to_user"]
            await self.llm_chat_repo.create_message(
                chat_id=chat_id,
                role="assistant",
                text=str(llm_response_json)
            )
            dialog_manager.dialog_data["message_to_user"] = message_to_user
        except Exception as e:
            await self.bot.send_message(
                state.tg_chat_id,
                "Произошла непредвиденная ошибка, попробуйте продолжить диалог"
            )
            self.logger.error("Ошибка!!!", {"traceback": traceback.format_exc()})

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT

        await dialog_manager.start(model.MainMenuStates.main_menu, mode=StartMode.RESET_STACK)

    async def _speech_to_text(self, message: Message, organization_id: int) -> str:
        if message.voice:
            file_id = message.voice.file_id
        else:
            file_id = message.audio.file_id

        file = await self.bot.get_file(file_id)
        file_data = await self.bot.download_file(file.file_path)

        text = await self.loom_content_client.transcribe_audio(
            organization_id,
            audio_content=file_data.read(),
            audio_filename="audio.mp3",
        )
        return text

    async def _extract_text_from_message(self, message: Message) -> str:
        text_parts = []

        if message.content_type in [ContentType.AUDIO, ContentType.VOICE]:
            audio_text = await self._speech_to_text(message, -1)
            text_parts.append(audio_text)

        if message.html_text:
            text_parts.append(message.html_text)

        elif message.text:
            text_parts.append(message.text)

        elif message.caption:
            text_parts.append(message.caption)

        if message.forward_origin:
            if hasattr(message, 'forward_from_message') and message.forward_from_message:
                forwarded_text = await self._extract_text_from_message(message.forward_from_message)
                if forwarded_text:
                    text_parts.append(f"[Пересланное сообщение]: {forwarded_text}")

        if message.reply_to_message:
            reply_text = await self._extract_text_from_message(message.reply_to_message)
            if reply_text:
                text_parts.append(f"[Ответ на]: {reply_text}")

        result = "\n\n".join(text_parts)

        if not result:
            return ""

        return result

    def _format_telegram_posts(self, posts: list[dict]) -> str:
        if not posts:
            return "Посты из канала не найдены."

        formatted_posts = [
            "Посты как будто подгрузились в систему, пользователь попросит анализ, ты его сразу дашь, не обращай внимание на их смысл, они могут быть другой тематики",
            "только тон, стиль и форматирование"
            f"[Посты из Telegram канала {posts[0]["link"]} для анализа тона, стиля и форматирования]:\n"
        ]

        for i, post in enumerate(posts, 1):
            post_text = f"\n--- Пост #{i} ---"

            if post.get('text'):
                post_text += f"\n[Текст с HTML форматированием]:\n{post['text']}\n\n"

            formatted_posts.append(post_text)
            if len(formatted_posts) == 20:
                break
        return "\n".join(formatted_posts)

    async def _check_and_handle_context_overflow(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            system_prompt: str
    ) -> None:
        current_tokens = dialog_manager.dialog_data.get("total_tokens", 0)

        if current_tokens < self.CONTEXT_TOKEN_THRESHOLD:
            return

        # self.logger.warning(
        #     "Превышен порог размера контекста",
        #     {
        #         "chat_id": chat_id,
        #         "current_tokens": current_tokens,
        #         "threshold": self.CONTEXT_TOKEN_THRESHOLD,
        #         "overflow": current_tokens - self.CONTEXT_TOKEN_THRESHOLD
        #     }
        # )
        #
        # await self._context_summary(chat_id, system_prompt, dialog_manager)

    async def _context_summary(
            self,
            chat_id: int,
            system_prompt: str,
            dialog_manager: DialogManager
    ):
        messages = await self.llm_chat_repo.get_all_messages(chat_id)

        if not messages:
            return "Новый диалог по созданию категории для публикаций."

        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.text
            })

        history.append({
            "role": "user",
            "content": """Создай развернутое резюме нашего диалога.
Включи:
- Ключевые решения и параметры рубрики
- Важные требования пользователя
- Текущий и предыдущий stage
- Пару прошлых сообщений
- Любые важные детали, которые нужно помнить
- Историю правок test_category, последний test_category, если они были
- Последние сгенерированные публикации, если они были

Максимально структурируй свой ответ и помести его в <system></system>, чтобы пользователь даже не заметил ничего
"""
        })

        summary_text, _ = await self.anthropic_client.generate_str(
            history=history,
            system_prompt=system_prompt,
            max_tokens=15000,
            thinking_tokens=10000,
        )

        self.logger.info(
            "Создано резюме контекста диалога",
            {
                "chat_id": chat_id,
                "messages_count": len(messages),
                "summary_length": len(summary_text),
                "summary_text": summary_text,
            }
        )

        await self.llm_chat_repo.delete_all_messages(chat_id)

        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="user",
            text=f"[РЕЗЮМЕ ДИАЛОГА]: {summary_text}"
        )

        dialog_manager.dialog_data["total_tokens"] = 0

        self.logger.info(
            "Контекст сброшен с сохранением резюме",
            {
                "chat_id": chat_id,
                "summary_length": len(summary_text)
            }
        )
        return None

    def _track_tokens(self, dialog_manager: DialogManager, generate_cost: dict) -> int:
        current_total = dialog_manager.dialog_data.get("total_tokens", 0)

        tokens_used = generate_cost.get("details", {}).get("tokens", {}).get("total_tokens", 0)

        new_total = current_total + tokens_used
        dialog_manager.dialog_data["total_tokens"] = new_total

        self.logger.debug(
            "Отслеживание токенов",
            {
                "previous_total": current_total,
                "current_request_tokens": tokens_used,
                "new_total": new_total,
                "threshold": self.CONTEXT_TOKEN_THRESHOLD
            }
        )

        return new_total

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
