from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient


class LoomEmployeeClient(interface.ILoomEmployeeClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            host: str,
            port: int
    ):
        logger = tel.logger()
        self.client = AsyncHTTPClient(
            host,
            port,
            prefix="/api/employee",
            use_tracing=True,
        )
        self.tracer = tel.tracer()

    async def create_employee(
            self,
            organization_id: int,
            invited_from_account_id: int,
            account_id: int,
            name: str,
            role: str
    ) -> int:
        with self.tracer.start_as_current_span(
                "EmployeeClient.create_employee",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id,
                    "invited_from_account_id": invited_from_account_id,
                    "account_id": account_id,
                    "name": name,
                    "role": role.value if hasattr(role, 'value') else str(role)
                }
        ) as span:
            try:
                body = {
                    "organization_id": organization_id,
                    "invited_from_account_id": invited_from_account_id,
                    "account_id": account_id,
                    "name": name,
                    "role": role.value if hasattr(role, 'value') else str(role)
                }
                response = await self.client.post("/create", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response["employee_id"]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_employee_by_account_id(self, account_id: int) -> model.Employee | None:
        with self.tracer.start_as_current_span(
                "EmployeeClient.get_employee_by_account_id",
                kind=SpanKind.CLIENT,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/account/{account_id}")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                if json_response:
                    return model.Employee(**json_response[0])
                else:
                    return None
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_employees_by_organization(self, organization_id: int) -> list[model.Employee]:
        with self.tracer.start_as_current_span(
                "EmployeeClient.get_employees_by_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/organization/{organization_id}/employees")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return [model.Employee(**emp) for emp in json_response["employees"]]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def update_employee_permissions(
            self,
            account_id: int,
            required_moderation: bool = None,
            autoposting_permission: bool = None,
            add_employee_permission: bool = None,
            edit_employee_perm_permission: bool = None,
            top_up_balance_permission: bool = None,
            sign_up_social_net_permission: bool = None
    ) -> None:
        with self.tracer.start_as_current_span(
                "EmployeeClient.update_employee_permissions",
                kind=SpanKind.CLIENT,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
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

                await self.client.put(f"/permissions", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def update_employee_role(
            self,
            account_id: int,
            role: str
    ) -> None:
        with self.tracer.start_as_current_span(
                "EmployeeClient.update_employee_role",
                kind=SpanKind.CLIENT,
                attributes={
                    "account_id": account_id,
                    "role": role
                }
        ) as span:
            try:
                body = {
                    "role": role.value if hasattr(role, 'value') else str(role)
                }
                await self.client.put(f"/{account_id}/role", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_employee(self, account_id: int) -> None:
        with self.tracer.start_as_current_span(
                "EmployeeClient.delete_employee",
                kind=SpanKind.CLIENT,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                await self.client.delete(f"/{account_id}")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def check_employee_permission(
            self,
            account_id: int,
            permission_type: str
    ) -> bool:
        with self.tracer.start_as_current_span(
                "EmployeeClient.check_employee_permission",
                kind=SpanKind.CLIENT,
                attributes={
                    "account_id": account_id,
                    "permission_type": permission_type
                }
        ) as span:
            try:
                params = {"permission_type": permission_type}
                response = await self.client.get(f"/{account_id}/permissions/check", params=params)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response["has_permission"]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise