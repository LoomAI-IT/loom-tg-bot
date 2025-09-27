from typing import Protocol
from abc import abstractmethod

from internal import model


class ILoomAccountClient(Protocol):

    @abstractmethod
    async def register(self, login: str, password: str) -> model.AuthorizationDataDTO: pass

    @abstractmethod
    async def register_from_tg(self, login: str, password: str) -> model.AuthorizationDataDTO: pass

    @abstractmethod
    async def login(self, login: str, password: str) -> model.AuthorizationDataDTO: pass

    @abstractmethod
    async def set_two_fa_key(
            self,
            access_token: str,
            account_id: int,
            google_two_fa_key: str,
            google_two_fa_code: str
    ) -> None: pass

    @abstractmethod
    async def delete_two_fa_key(
            self,
            access_token: str,
            account_id: int,
            google_two_fa_code: str
    ) -> None: pass

    @abstractmethod
    async def verify_two(
            self,
            access_token: str,
            account_id: int,
            google_two_fa_code: str
    ) -> bool: pass

    @abstractmethod
    async def recovery_password(
            self,
            access_token: str,
            account_id: int,
            new_password: str
    ) -> None: pass

    @abstractmethod
    async def change_password(
            self,
            access_token: str,
            account_id: int,
            new_password: str,
            old_password: str
    ) -> None: pass


class IPaymentClient(Protocol):
    # Этот интерфейс пустой, так как файл pkg/client/internal/loom_payment/client.py пустой
    pass
