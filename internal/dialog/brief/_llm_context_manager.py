from aiogram_dialog import DialogManager

from internal import interface


class _LLMContextManager:
    def __init__(
            self,
            logger,
            anthropic_client: interface.IAnthropicClient,
            llm_chat_repo: interface.ILLMChatRepo
    ):
        self.logger = logger
        self.anthropic_client = anthropic_client
        self.llm_chat_repo = llm_chat_repo
        self.CONTEXT_TOKEN_THRESHOLD = 30000

    def track_tokens(self, dialog_manager: DialogManager, generate_cost: dict) -> int:
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

    async def check_and_handle_context_overflow(
            self,
            dialog_manager: DialogManager,
            chat_id: int,
            system_prompt: str
    ) -> None:
        current_tokens = dialog_manager.dialog_data.get("total_tokens", 0)

        if current_tokens < self.CONTEXT_TOKEN_THRESHOLD:
            return

        # Закомментировано, так как в оригинальном коде тоже закомментировано
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
        # await self.context_summary(chat_id, system_prompt, dialog_manager)

    async def context_summary(
            self,
            chat_id: int,
            system_prompt: str,
            dialog_manager: DialogManager
    ):
        """Создание резюме диалога при переполнении контекста"""
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
            "content": """
Создай развернутое резюме нашего диалога.
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
