from internal import interface


class _ChatManager:
    def __init__(self, logger, llm_chat_repo: interface.ILLMChatRepo):
        self.logger = logger
        self.llm_chat_repo = llm_chat_repo

    async def clear_chat(self, state_id: int) -> None:
        chat = await self.llm_chat_repo.get_chat_by_state_id(state_id)
        if chat:
            await self.llm_chat_repo.delete_chat(chat[0].id)
            self.logger.info(f"Чат удален для state_id: {state_id}")
