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

from internal.dialog._state_helper import _StateHelper
from internal.dialog._message_extractor import _MessageExtractor
from internal.dialog.brief._llm_context_manager import _LLMContextManager
from internal.dialog.brief._telegram_post_formatter import _TelegramPostFormatter


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

        # Инициализация приватных сервисов
        self._state_helper = _StateHelper(state_repo)
        self._llm_context_manager = _LLMContextManager(self.logger, anthropic_client, llm_chat_repo)
        self._message_extractor = _MessageExtractor(self.logger, bot, loom_content_client)
        self._telegram_post_formatter = _TelegramPostFormatter()

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

            user_text = await self._message_extractor.extract_text_from_message(message)
            if not user_text:
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

            await self._llm_context_manager.check_and_handle_context_overflow(dialog_manager, chat_id, system_prompt)

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

            self._llm_context_manager.track_tokens(dialog_manager, generate_cost)

            if llm_response_json.get("telegram_channel_username_list"):
                telegram_channel_username_list = llm_response_json.get("telegram_channel_username_list")

                all_telegram_posts = []
                for telegram_channel_username in telegram_channel_username_list:
                    telegram_posts = await self.telegram_client.get_channel_posts(
                        telegram_channel_username,
                        10
                    )
                    all_telegram_posts.extend(telegram_posts)

                message_to_llm = f"""
<system>
{self._telegram_posts_formatter.format_telegram_posts(all_telegram_posts)}
</system>

<user>
Проведи анализ постов из каналов
</user>
"""
                await self.llm_chat_repo.create_message(
                    chat_id=chat_id,
                    role="user",
                    text=f'{{"message_to_llm": {message_to_llm}}}'
                )

                await self._llm_context_manager.check_and_handle_context_overflow(dialog_manager, chat_id, system_prompt)

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

                self._llm_context_manager.track_tokens(dialog_manager, generate_cost)

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

                await self._llm_context_manager.check_and_handle_context_overflow(dialog_manager, chat_id, system_prompt)

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
                self._llm_context_manager.track_tokens(dialog_manager, generate_cost)

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
    async def handle_confirm_cancel(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager)
        await callback.answer()

        await dialog_manager.start(model.MainMenuStates.main_menu, mode=StartMode.RESET_STACK)

    @auto_log()
    @traced_method()
    async def handle_go_to_main_menu(
            self,
            callback: CallbackQuery,
            button: Button,
            dialog_manager: DialogManager
    ) -> None:
        self._state_helper.set_edit_mode(dialog_manager)

        await dialog_manager.start(model.MainMenuStates.main_menu, mode=StartMode.RESET_STACK)
