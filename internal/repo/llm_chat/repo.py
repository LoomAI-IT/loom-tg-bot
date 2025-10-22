from pkg.trace_wrapper import traced_method
from .sql_query import *
from internal import model
from internal import interface


class LLMChatRepo(interface.ILLMChatRepo):
    def __init__(self, tel: interface.ITelemetry, db: interface.IDB):
        self.db = db
        self.tracer = tel.tracer()

    @traced_method()
    async def create_chat(self, state_id: int) -> int:
        args = {'state_id': state_id}
        chat_id = await self.db.insert(create_llm_chat, args)
        return chat_id

    @traced_method()
    async def get_chat_by_id(self, chat_id: int) -> list[model.LLMChat]:
        args = {'chat_id': chat_id}
        rows = await self.db.select(get_llm_chat_by_id, args)
        if rows:
            rows = model.LLMChat.serialize(rows)
        return rows

    @traced_method()
    async def get_chat_by_state_id(self, state_id: int) -> list[model.LLMChat]:
        args = {'state_id': state_id}
        rows = await self.db.select(get_llm_chat_by_state_id, args)
        if rows:
            rows = model.LLMChat.serialize(rows)
        return rows

    @traced_method()
    async def delete_chat(self, chat_id: int) -> None:
        args = {'chat_id': chat_id}
        await self.db.delete(delete_llm_chat, args)

    @traced_method()
    async def create_message(self, chat_id: int, role: str, text: str) -> int:
        args = {
            'chat_id': chat_id,
            'role': role,
            'text': text,
        }
        message_id = await self.db.insert(create_llm_message, args)
        return message_id

    @traced_method()
    async def get_all_messages(self, chat_id: int) -> list[model.LLMMessage]:
        args = {'chat_id': chat_id}
        rows = await self.db.select(get_all_messages_by_chat_id, args)
        if rows:
            return model.LLMMessage.serialize(rows)
        return []

    @traced_method()
    async def delete_all_messages(self, chat_id: int) -> None:
        args = {'chat_id': chat_id}
        await self.db.delete(delete_all_messages_by_chat_id, args)

    @traced_method()
    async def get_message_by_id(self, message_id: int) -> list[model.LLMMessage]:
        args = {'message_id': message_id}
        rows = await self.db.select(get_message_by_id, args)
        if rows:
            rows = model.LLMMessage.serialize(rows)
        return rows

    @traced_method()
    async def delete_message(self, message_id: int) -> None:
        args = {'message_id': message_id}
        await self.db.delete(delete_message_by_id, args)