from contextvars import ContextVar
from typing import Callable
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from opentelemetry import propagate
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface
from internal import common
from pkg.trace_wrapper import traced_method


class HttpMiddleware(interface.IHttpMiddleware):
    def __init__(
            self,
            tel: interface.ITelemetry,
            prefix: str,
            log_context: ContextVar[dict],
    ):
        self.tracer = tel.tracer()
        self.meter = tel.meter()
        self.logger = tel.logger()
        self.prefix = prefix
        self.log_context = log_context

    def trace_middleware01(self, app: FastAPI):
        @app.middleware("http")
        async def _trace_middleware01(request: Request, call_next: Callable):
            if self.prefix not in request.url.path:
                return JSONResponse(
                    status_code=404,
                    content={"error": "not found"}
                )
            with self.tracer.start_as_current_span(
                    f"{request.method} {request.url.path}",
                    context=propagate.extract(dict(request.headers)),
                    kind=SpanKind.SERVER,
                    attributes={
                        SpanAttributes.HTTP_ROUTE: str(request.url.path),
                        SpanAttributes.HTTP_METHOD: request.method,
                    }
            ) as root_span:
                try:
                    response = await call_next(request)

                    status_code = response.status_code
                    response_size = response.headers.get("content-length")

                    root_span.set_attributes({
                        SpanAttributes.HTTP_STATUS_CODE: status_code,
                    })

                    if response_size:
                        try:
                            root_span.set_attribute(SpanAttributes.HTTP_RESPONSE_BODY_SIZE, int(response_size))
                        except ValueError:
                            pass

                    root_span.set_status(Status(StatusCode.OK))

                    return response

                except Exception as err:
                    root_span.set_status(StatusCode.ERROR, str(err))
                    return JSONResponse(
                        status_code=500,
                        content={"message": "Internal Server Error"},
                    )

        return _trace_middleware01

    def logger_middleware02(self, app: FastAPI):
        @app.middleware("http")
        async def _logger_middleware02(request: Request, call_next: Callable):
            context_token = self.log_context.set({
                common.TELEGRAM_USER_USERNAME_KEY: request.headers.get(common.TELEGRAM_USER_USERNAME_KEY, ""),
                common.TELEGRAM_CHAT_ID_KEY: request.headers.get(common.TELEGRAM_CHAT_ID_KEY, "0"),
                common.TELEGRAM_EVENT_TYPE_KEY: request.headers.get(common.TELEGRAM_EVENT_TYPE_KEY, ""),
                common.ORGANIZATION_ID_KEY: request.headers.get(common.ORGANIZATION_ID_KEY, "0"),
                common.ACCOUNT_ID_KEY: request.headers.get(common.ACCOUNT_ID_KEY, "0"),
            })
            try:
                response = await call_next(request)

                status_code = response.status_code

                if 400 <= status_code < 500:
                    self.logger.warning("Обработка HTTP запроса завершена с ошибкой клиента")

                return response
            finally:
                self.log_context.reset(context_token)

        return _logger_middleware02
