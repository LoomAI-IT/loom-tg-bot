from typing import Protocol
from abc import abstractmethod
from internal import model


class ILoomEmployeeClient(Protocol):

    @abstractmethod
    async def create_employee(
            self,
            organization_id: int,
            invited_from_account_id: int,
            account_id: int,
            name: str,
            role: str
    ) -> int: pass

    @abstractmethod
    async def get_employee_by_account_id(self, account_id: int) -> model.Employee | None: pass

    @abstractmethod
    async def get_employees_by_organization(self, organization_id: int) -> list[model.Employee]: pass

    @abstractmethod
    async def update_employee_permissions(
            self,
            account_id: int,
            required_moderation: bool = None,
            autoposting_permission: bool = None,
            add_employee_permission: bool = None,
            edit_employee_perm_permission: bool = None,
            top_up_balance_permission: bool = None,
            sign_up_social_net_permission: bool = None
    ) -> None: pass

    @abstractmethod
    async def update_employee_role(
            self,
            account_id: int,
            role: str
    ) -> None: pass

    @abstractmethod
    async def delete_employee(self, account_id: int) -> None: pass

    @abstractmethod
    async def check_employee_permission(
            self,
            account_id: int,
            permission_type: str
    ) -> bool: pass
