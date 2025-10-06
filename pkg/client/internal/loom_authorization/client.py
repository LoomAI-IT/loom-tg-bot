from contextvars import ContextVar

from opentelemetry.trace import SpanKind

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient
from pkg.trace_wrapper import traced_method


class LoomAuthorizationClient(interface.ILoomAuthorizationClient):
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
            prefix="/api/authorization",
            use_tracing=True,
            log_context=log_context
        )
        self.tracer = tel.tracer()

    @traced_method(SpanKind.CLIENT)
    async def authorization_tg(self, account_id: int) -> model.JWTTokens:
        body = {
            "account_id": account_id
        }
        response = await self.client.post("/tg", json=body)
        json_response = response.json()

        return model.JWTTokens(**json_response)

    @traced_method(SpanKind.CLIENT)
    async def check_authorization(self, access_token: str) -> model.AuthorizationData:
        cookies = {"Access-Token": access_token}
        response = await self.client.get("/check", cookies=cookies)
        json_response = response.json()

        return model.AuthorizationData(**json_response)
