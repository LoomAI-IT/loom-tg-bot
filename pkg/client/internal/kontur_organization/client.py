from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient


class OrganizationClient(interface.IOrganizationService):
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
            prefix="/api/organization",
            use_tracing=True,
            logger=logger,
        )
        self.tracer = tel.tracer()

    async def create_organization(
            self,
            name: str
    ) -> int:
        with self.tracer.start_as_current_span(
                "OrganizationClient.create_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "name": name
                }
        ) as span:
            try:
                body = {
                    "name": name
                }
                response = await self.client.post("/", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return json_response["organization_id"]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_organization_by_id(self, organization_id: int) -> model.Organization:
        with self.tracer.start_as_current_span(
                "OrganizationClient.get_organization_by_id",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                response = await self.client.get(f"/{organization_id}")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return model.Organization(**json_response)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def get_all_organizations(self) -> list[model.Organization]:
        with self.tracer.start_as_current_span(
                "OrganizationClient.get_all_organizations",
                kind=SpanKind.CLIENT,
        ) as span:
            try:
                response = await self.client.get("/")
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return [model.Organization(**org) for org in json_response["organizations"]]
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def update_organization(
            self,
            organization_id: int,
            name: str = None,
            autoposting_moderation: bool = None,
            video_cut_description_end_sample: str = None,
            publication_text_end_sample: str = None,
    ) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationClient.update_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
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

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_organization(self, organization_id: int) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationClient.delete_organization",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id
                }
        ) as span:
            try:
                await self.client.delete(f"/{organization_id}")

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def top_up_balance(self, organization_id: int, amount_rub: int) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationClient.top_up_balance",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id,
                    "amount_rub": amount_rub
                }
        ) as span:
            try:
                body = {
                    "organization_id": organization_id,
                    "amount_rub": amount_rub
                }
                await self.client.post("/balance/top-up", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def debit_balance(self, organization_id: int, amount_rub: int) -> None:
        with self.tracer.start_as_current_span(
                "OrganizationClient.debit_balance",
                kind=SpanKind.CLIENT,
                attributes={
                    "organization_id": organization_id,
                    "amount_rub": amount_rub
                }
        ) as span:
            try:
                body = {
                    "organization_id": organization_id,
                    "amount_rub": amount_rub
                }
                await self.client.post("/balance/debit", json=body)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise