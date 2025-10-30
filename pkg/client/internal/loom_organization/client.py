from contextvars import ContextVar

import httpx
from opentelemetry.trace import SpanKind

from internal import model
from internal import interface
from internal import common
from pkg.client.client import AsyncHTTPClient
from pkg.trace_wrapper import traced_method


class LoomOrganizationClient(interface.ILoomOrganizationClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            host: str,
            port: int,
            interserver_secret_key: str,
            log_context: ContextVar[dict],
    ):
        logger = tel.logger()
        self.client = AsyncHTTPClient(
            host,
            port,
            prefix="/api/organization",
            use_tracing=True,
            log_context=log_context
        )
        self.tracer = tel.tracer()
        self.interserver_secret_key = interserver_secret_key

    @traced_method(SpanKind.CLIENT)
    async def create_organization(self, name: str) -> int:
        body = {
            "name": name,
        }
        response = await self.client.post(f"/create", json=body)
        json_response = response.json()

        return json_response["organization_id"]

    @traced_method(SpanKind.CLIENT)
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
    ) -> None:
        body: dict = {
            "organization_id": organization_id,
        }

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if tone_of_voice is not None:
            body["tone_of_voice"] = tone_of_voice
        if compliance_rules is not None:
            body["compliance_rules"] = compliance_rules
        if products is not None:
            body["products"] = products
        if locale is not None:
            body["locale"] = locale
        if additional_info is not None:
            body["additional_info"] = additional_info

        await self.client.put(f"", json=body)

    @traced_method(SpanKind.CLIENT)
    async def get_organization_by_id(self, organization_id: int) -> model.Organization:

        response = await self.client.get(f"/{organization_id}")
        json_response = response.json()

        return model.Organization(**json_response)

    @traced_method(SpanKind.CLIENT)
    async def get_all_organizations(self) -> list[model.Organization]:
        response = await self.client.get("/all")
        json_response = response.json()

        return [model.Organization(**org) for org in json_response["organizations"]]


    @traced_method(SpanKind.CLIENT)
    async def top_up_balance(self, organization_id: int, amount_rub: int) -> None:
        body = {
            "organization_id": organization_id,
            "amount_rub": amount_rub
        }
        await self.client.post("/balance/top-up", json=body)

    @traced_method(SpanKind.CLIENT)
    async def debit_balance(self, organization_id: int, amount_rub: str) -> None:
        body = {
            "organization_id": organization_id,
            "amount_rub": amount_rub,
            "interserver_secret_key": self.interserver_secret_key,
        }
        try:
            await self.client.post("/balance/debit", json=body)
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 400:
                try:
                    response_data = err.response.json()
                    if response_data.get("insufficient_balance"):
                        raise common.ErrInsufficientBalance()
                except Exception:
                    pass
            raise

    @traced_method(SpanKind.CLIENT)
    async def get_cost_multiplier(self, organization_id: int) -> model.CostMultiplier:
        response = await self.client.get(f"/cost-multiplier/{organization_id}")
        json_response = response.json()

        return model.CostMultiplier(**json_response)
