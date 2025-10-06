from contextvars import ContextVar

from opentelemetry.trace import SpanKind

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient
from pkg.trace_wrapper import traced_method


class LoomOrganizationClient(interface.ILoomOrganizationClient):
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
            prefix="/api/organization",
            use_tracing=True,
            log_context=log_context
        )
        self.tracer = tel.tracer()

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
    async def update_organization(
            self,
            organization_id: int,
            name: str = None,
            autoposting_moderation: bool = None,
            video_cut_description_end_sample: str = None,
            publication_text_end_sample: str = None,
    ) -> None:
        body = {}
        if name is not None:
            body["name"] = name
        if autoposting_moderation is not None:
            body["autoposting_moderation"] = autoposting_moderation
        if video_cut_description_end_sample is not None:
            body["video_cut_description_end_sample"] = video_cut_description_end_sample
        if publication_text_end_sample is not None:
            body["publication_text_end_sample"] = publication_text_end_sample

        await self.client.put(f"/{organization_id}", json=body)

    @traced_method(SpanKind.CLIENT)
    async def top_up_balance(self, organization_id: int, amount_rub: int) -> None:
        body = {
            "organization_id": organization_id,
            "amount_rub": amount_rub
        }
        await self.client.post("/balance/top-up", json=body)

    @traced_method(SpanKind.CLIENT)
    async def debit_balance(self, organization_id: int, amount_rub: int) -> None:
        body = {
            "organization_id": organization_id,
            "amount_rub": amount_rub
        }
        await self.client.post("/balance/debit", json=body)
