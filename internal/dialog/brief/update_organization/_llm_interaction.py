from typing import Dict, Any, List

from aiogram import Bot
from aiogram.types import Message

from internal import interface
from pkg.tg_action_wrapper import tg_action


class _LLMInteraction:
    """Класс для взаимодействия с LLM и обработки диалогов"""

    def __init__(
            self,
            logger,
            bot: Bot,
            anthropic_client: interface.IAnthropicClient,
            update_organization_prompt_generator: interface.IUpdateOrganizationPromptGenerator,
            loom_organization_client: interface.ILoomOrganizationClient,
            llm_chat_repo: interface.ILLMChatRepo
    ):
        self.logger = logger
        self.bot = bot
        self.anthropic_client = anthropic_client
        self.update_organization_prompt_generator = update_organization_prompt_generator
        self.loom_organization_client = loom_organization_client
        self.llm_chat_repo = llm_chat_repo

    async def process_user_message(
            self,
            chat_id: int,
            user_text: str,
            organization_id: int,
            message: Message
    ) -> Dict[str, Any]:
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
            text=user_text
        )

        organization = await self.loom_organization_client.get_organization_by_id(organization_id)
        system_prompt = await self.update_organization_prompt_generator.get_update_organization_system_prompt(
            organization
        )

        messages = await self.llm_chat_repo.get_all_messages(chat_id)
        history = self._build_message_history(messages)

        async with tg_action(self.bot, message.chat.id):
            llm_response_json, _ = await self.anthropic_client.generate_json(
                history=history,
                system_prompt=system_prompt,
                max_tokens=15000,
                enable_web_search=False,
                thinking_tokens=10000
            )

        return llm_response_json

    async def save_assistant_message(self, chat_id: str, message_text: str) -> None:
        """Сохраняет сообщение ассистента в историю чата"""
        await self.llm_chat_repo.create_message(
            chat_id=chat_id,
            role="assistant",
            text=message_text
        )

    @staticmethod
    def _build_message_history(messages: List) -> List[Dict[str, str]]:
        """Формирует историю сообщений для LLM"""
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.text
            })
        return history
