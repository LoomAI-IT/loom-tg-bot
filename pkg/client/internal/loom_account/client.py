from contextvars import ContextVar

from opentelemetry.trace import SpanKind

from internal import interface, model
from pkg.client.client import AsyncHTTPClient
from pkg.trace_wrapper import traced_method


class LoomAccountClient(interface.ILoomAccountClient):
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
            prefix="/api/account",
            use_tracing=True,
            log_context=log_context
        )
        self.tracer = tel.tracer()

    @traced_method(SpanKind.CLIENT)
    async def register(self, login: str, password: str) -> model.AuthorizationDataDTO:
        body = {
            "login": login,
            "password": password
        }
        response = await self.client.post("/register", json=body)
        json_response = response.json()

        return model.AuthorizationDataDTO(
            account_id=json_response["account_id"],
            access_token=response.cookies.get("Access-Token"),
            refresh_token=response.cookies.get("Refresh-Token"),
        )

    @traced_method(SpanKind.CLIENT)
    async def register_from_tg(self, login: str, password: str) -> model.AuthorizationDataDTO:
        body = {
            "login": login,
            "password": password
        }
        response = await self.client.post("/register/tg", json=body)
        json_response = response.json()

        return model.AuthorizationDataDTO(
            account_id=json_response["account_id"],
            access_token=response.cookies.get("Access-Token"),
            refresh_token=response.cookies.get("Refresh-Token"),
        )

    @traced_method(SpanKind.CLIENT)
    async def login(
            self,
            login: str,
            password: str,
    ) -> model.AuthorizationDataDTO:
        body = {
            "login": login,
            "password": password
        }
        response = await self.client.post("/login", json=body)
        json_response = response.json()

        return model.AuthorizationDataDTO(
            account_id=json_response["account_id"],
            access_token=response.cookies.get("Access-Token"),
            refresh_token=response.cookies.get("Refresh-Token"),
        )

    # async def generate_two_fa_key(self, account_id: int) -> tuple[str, io.BytesIO]:
    #     with self.tracer.start_as_current_span(
    #             "AccountClient.generate_two_fa_key",
    #             kind=SpanKind.CLIENT,
    #             attributes={
    #                 "account_id": account_id
    #             }
    #     ) as span:
    #         try:
    #             headers = {"X-Account-ID": str(account_id)}
    #             response = await self.client.get("/two-fa/generate", headers=headers)
    #
    #             # Assuming response contains both key and QR code data
    #             json_response = response.json()
    #             key = json_response["key"]
    #             qr_code_bytes = io.BytesIO(bytes.fromhex(json_response["qr_code_hex"]))
    #
    #             span.set_status(Status(StatusCode.OK))
    #             return key, qr_code_bytes
    #         except Exception as e:
    #             (e)
    #             span.set_status(Status(StatusCode.ERROR, str(e)))
    #             raise

    @traced_method(SpanKind.CLIENT)
    async def set_two_fa_key(
            self,
            access_token: str,
            account_id: int,
            google_two_fa_key: str,
            google_two_fa_code: str
    ) -> None:
        cookies = {
            "Access-Token": access_token,
        }
        body = {
            "account_id": account_id,
            "google_two_fa_key": google_two_fa_key,
            "google_two_fa_code": google_two_fa_code
        }
        await self.client.post("/two-fa/set", json=body, cookies=cookies)

    @traced_method(SpanKind.CLIENT)
    async def delete_two_fa_key(
            self,
            access_token: str,
            account_id: int,
            google_two_fa_code: str
    ) -> None:
        cookies = {
            "Access-Token": access_token,
        }
        body = {
            "google_two_fa_code": google_two_fa_code
        }
        await self.client.delete("/two-fa", json=body, cookies=cookies)

    @traced_method(SpanKind.CLIENT)
    async def verify_two(
            self,
            access_token: str,
            account_id: int,
            google_two_fa_code: str
    ) -> bool:
        cookies = {
            "Access-Token": access_token,
        }
        body = {
            "account_id": account_id,
            "google_two_fa_code": google_two_fa_code
        }
        response = await self.client.post("/two-fa/verify", json=body, cookies=cookies)
        json_response = response.json()

        return json_response["verified"]

    @traced_method(SpanKind.CLIENT)
    async def recovery_password(
            self,
            access_token: str,
            account_id: int,
            new_password: str
    ) -> None:
        cookies = {
            "Access-Token": access_token,
        }
        body = {
            "account_id": account_id,
            "new_password": new_password
        }
        await self.client.post("/password/recovery", json=body, cookies=cookies)

    @traced_method(SpanKind.CLIENT)
    async def change_password(
            self,
            access_token: str,
            account_id: int,
            new_password: str,
            old_password: str
    ) -> None:
        cookies = {
            "Access-Token": access_token,
        }
        body = {
            "account_id": account_id,
            "new_password": new_password,
            "old_password": old_password
        }
        await self.client.put("/password", json=body, cookies=cookies)
