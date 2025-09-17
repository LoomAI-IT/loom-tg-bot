from typing import Protocol
from abc import abstractmethod

from internal import model


class IKonturAuthorizationClient(Protocol):

    @abstractmethod
    async def authorization_rg(self, account_id: int) -> model.JWTTokens: pass

    @abstractmethod
    async def check_authorization(self, access_token: str) -> model.AuthorizationData: pass
