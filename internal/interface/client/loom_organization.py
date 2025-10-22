from typing import Protocol
from abc import abstractmethod

from internal import model


class ILoomOrganizationClient(Protocol):

    @abstractmethod
    async def create_organization(self, name: str) -> int: pass

    @abstractmethod
    async def update_organization(
            self,
            organization_id: int,
            name: str = None,
            description: str = None,
            tone_of_voice: list[str] = None,
            compliance_rules: list[dict] = None,
            products: list[dict] = None,
            locale: dict = None,
            additional_info: list[dict] = None
    ) -> None: pass

    @abstractmethod
    async def get_organization_by_id(self, organization_id: int) -> model.Organization: pass

    @abstractmethod
    async def get_all_organizations(self) -> list[model.Organization]: pass

    @abstractmethod
    async def top_up_balance(self, organization_id: int, amount_rub: int) -> None: pass

    @abstractmethod
    async def debit_balance(self, organization_id: int, amount_rub: int) -> None: pass
