from typing import Protocol
from abc import abstractmethod

from internal import model


class ILLMChatRepo(Protocol):
    @abstractmethod
    async def create_chat(self, state_id: int) -> int:
        pass

    @abstractmethod
    async def get_chat_by_id(self, chat_id: int) -> list[model.LLMChat]:
        pass

    @abstractmethod
    async def get_chat_by_state_id(self, state_id: int) -> list[model.LLMChat]:
        pass

    @abstractmethod
    async def delete_chat(self, chat_id: int) -> None:
        pass

    @abstractmethod
    async def create_message(self, chat_id: int, role: str, text: str) -> int:
        pass

    @abstractmethod
    async def get_all_messages(self, chat_id: int) -> list[model.LLMMessage]:
        pass

    @abstractmethod
    async def delete_all_messages(self, chat_id: int) -> None:
        pass

    @abstractmethod
    async def get_message_by_id(self, message_id: int) -> list[model.LLMMessage]:
        pass

    @abstractmethod
    async def delete_message(self, message_id: int) -> None:
        pass