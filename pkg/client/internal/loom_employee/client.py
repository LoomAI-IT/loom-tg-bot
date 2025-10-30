from contextvars import ContextVar

from opentelemetry.trace import SpanKind

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient
from pkg.trace_wrapper import traced_method


class LoomEmployeeClient(interface.ILoomEmployeeClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            host: str,
            port: int,
            log_context: ContextVar[dict],
    ):
        logger = tel.logger()
        self.client = AsyncHTTPClient(
            host,
            port,
            prefix="/api/employee",
            use_tracing=True,
            log_context=log_context
        )
        self.tracer = tel.tracer()

    @traced_method(SpanKind.CLIENT)
    async def create_employee(
            self,
            organization_id: int,
            invited_from_account_id: int,
            account_id: int,
            name: str,
            role: str
    ) -> int:
        body = {
            "organization_id": organization_id,
            "invited_from_account_id": invited_from_account_id,
            "account_id": account_id,
            "name": name,
            "role": role.value if hasattr(role, 'value') else str(role)
        }
        response = await self.client.post("/create", json=body)
        json_response = response.json()

        return json_response["employee_id"]

    @traced_method(SpanKind.CLIENT)
    async def get_employee_by_account_id(self, account_id: int) -> model.Employee | None:
        response = await self.client.get(f"/account/{account_id}")
        json_response = response.json()

        if json_response:
            return model.Employee(**json_response[0])
        else:
            return None

    @traced_method(SpanKind.CLIENT)
    async def get_employees_by_organization(self, organization_id: int) -> list[model.Employee]:
        response = await self.client.get(f"/organization/{organization_id}/employees")
        json_response = response.json()

        return [model.Employee(**emp) for emp in json_response["employees"]]

    @traced_method(SpanKind.CLIENT)
    async def update_employee_permissions(
            self,
            account_id: int,
            required_moderation: bool = None,
            autoposting_permission: bool = None,
            add_employee_permission: bool = None,
            edit_employee_perm_permission: bool = None,
            top_up_balance_permission: bool = None,
            sign_up_social_net_permission: bool = None,
            setting_category_permission: bool = None,
            setting_organization_permission: bool = None
    ) -> None:
        body = {"account_id": account_id}
        if required_moderation is not None:
            body["required_moderation"] = required_moderation
        if autoposting_permission is not None:
            body["autoposting_permission"] = autoposting_permission
        if add_employee_permission is not None:
            body["add_employee_permission"] = add_employee_permission
        if edit_employee_perm_permission is not None:
            body["edit_employee_perm_permission"] = edit_employee_perm_permission
        if top_up_balance_permission is not None:
            body["top_up_balance_permission"] = top_up_balance_permission
        if sign_up_social_net_permission is not None:
            body["sign_up_social_net_permission"] = sign_up_social_net_permission
        if setting_category_permission is not None:
            body["setting_category_permission"] = setting_category_permission
        if setting_organization_permission is not None:
            body["setting_organization_permission"] = setting_organization_permission

        await self.client.put(f"/permissions", json=body)

    @traced_method(SpanKind.CLIENT)
    async def update_employee_role(
            self,
            account_id: int,
            role: str
    ) -> None:
        body = {
            "role": role.value if hasattr(role, 'value') else str(role)
        }
        await self.client.put(f"/{account_id}/role", json=body)

    @traced_method(SpanKind.CLIENT)
    async def delete_employee(self, account_id: int) -> None:
        await self.client.delete(f"/{account_id}")

    @traced_method(SpanKind.CLIENT)
    async def check_employee_permission(
            self,
            account_id: int,
            permission_type: str
    ) -> bool:
        params = {"permission_type": permission_type}
        response = await self.client.get(f"/{account_id}/permissions/check", params=params)
        json_response = response.json()

        return json_response["has_permission"]
