from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.tg_action_wrapper import tg_action
from pkg.trace_wrapper import traced_method


class UpdateCategoryService(interface.IUpdateCategoryService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            update_category_prompt_generator: interface.IUpdateCategoryPromptGenerator,
            loom_organization_client: interface.ILoomOrganizationClient,
            loom_content_client: interface.ILoomContentClient,
            llm_chat_repo: interface.ILLMChatRepo,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.update_category_prompt_generator = update_category_prompt_generator
        self.loom_organization_client = loom_organization_client
        self.loom_content_client = loom_content_client
        self.llm_chat_repo = llm_chat_repo
        self.state_repo = state_repo

    @auto_log()
    @traced_method()
    async def handle_select_category(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            category_id: str
    ) -> None:
        dialog_manager.show_mode = ShowMode.EDIT
        await callback.answer()

        category = await self.loom_content_client.get_category_by_id(
            int(category_id)
        )

        dialog_manager.dialog_data["category_id"] = category.id
        dialog_manager.dialog_data["category_name"] = category.name

        await dialog_manager.switch_to(model.UpdateCategoryStates.update_category)

    @auto_log()
    @traced_method()
    async def handle_user_message(
            self,
            message: Message,
            widget: MessageInput,
            dialog_manager: DialogManager
    ) -> None:
        dialog_manager.show_mode = ShowMode.SEND

        state = await self._get_state(dialog_manager)

        category_id = dialog_manager.dialog_data.get("category_id")
        chat_id = dialog_manager.dialog_data.get("chat_id")
        user_text = await self._extract_text_from_message(message)

        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="user",
            text=user_text
        )
        organization = await self.loom_organization_client.get_organization_by_id(
            state.organization_id
        )
        category = await self.loom_content_client.get_category_by_id(
            category_id
        )
        system_prompt = await self.update_category_prompt_generator.get_update_category_system_prompt(
            organization,
            category,
        )
        messages = await self.llm_chat_repo.get_all_messages(chat_id)
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.text
            })

        async with tg_action(self.bot, message.chat.id):
            llm_response_json, _ = await self.anthropic_client.generate_json(
                history=history,
                system_prompt=system_prompt,
                max_tokens=15000,
                thinking_tokens=10000
            )

        if llm_response_json.get("test_category"):
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
                    good_samples=[],
                    bad_samples=[],
                    additional_info=test_category_data.get("additional_info", []),
                    prompt_for_image_style=test_category_data.get("prompt_for_image_style", ""),
                )

            await self.llm_chat_repo.create_message(
                chat_id=chat_id,
                role="user",
                text=f"""
<system>
[Сгенерированный тестовый пост]
{test_publication_text}
[Параметры рубрики с которыми генерировался пост]
{{
    "test_category": {test_category_data},
    "user_text_reference": {user_text_reference},
}}
</system>

<user>
"Покажи мне пост с моими правками, пост НЕ НУЖНО оборачивать ни в <blockquote>, ни в <pre>, оставь только те теги, которые изначально есть у поста
</user>
"""
            )

            messages = await self.llm_chat_repo.get_all_messages(chat_id)
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.text
                })

            async with tg_action(self.bot, message.chat.id):
                llm_response_json, _ = await self.anthropic_client.generate_json(
                    history=history,
                    system_prompt=system_prompt,
                    max_tokens=15000,
                    thinking_tokens=10000
                )

        if llm_response_json.get("final_category"):
            category_data = llm_response_json["final_category"]

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

            await dialog_manager.switch_to(model.UpdateCategoryStates.category_updated)
            return

        message_to_user = llm_response_json["message_to_user"]
        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="assistant",
            text=message_to_user
        )
        dialog_manager.dialog_data["message_to_user"] = message_to_user

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

        if message.text:
            text_parts.append(message.text)

        if message.caption:
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
            return f"[Сообщение типа {message.content_type} без текста]"

        return result

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
