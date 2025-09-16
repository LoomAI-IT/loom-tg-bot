from typing import Protocol
from abc import abstractmethod

from internal import model


class IStateService(Protocol):

    @abstractmethod
    async def create_state(self, tg_chat_id: int) -> int: pass

    @abstractmethod
    async def state_by_id(self, tg_chat_id: int) -> list[model.UserState]: pass

    @abstractmethod
    async def change_user_state(
            self,
            state_id: int,
            account_id: int = None,
            access_token: str = None,
            refresh_token: str = None,
    ) -> None: pass

    @abstractmethod
    async def delete_state_by_tg_chat_id(self, tg_chat_id: int) -> None: pass


class IStateRepo(Protocol):

    @abstractmethod
    async def create_state(self, tg_chat_id: int) -> int: pass

    @abstractmethod
    async def state_by_id(self, tg_chat_id: int) -> list[model.UserState]: pass

    @abstractmethod
    async def change_user_state(
            self,
            state_id: int,
            access_token: str = None,
            refresh_token: str = None,
    ) -> None: pass

    @abstractmethod
    async def delete_state_by_tg_chat_id(self, tg_chat_id: int) -> None: pass
