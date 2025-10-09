from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Optional, Callable

import httpx
from tenacity import (
    stop_after_attempt,
    AsyncRetrying,
    RetryCallState,
    wait_exponential,
)
from opentelemetry import propagate

from internal import interface


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        logger: Optional[interface.IOtelLogger] = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.logger = logger

        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = "closed"  # closed, open, half-open

    @property
    def state(self) -> str:
        return self._state

    async def call(self, func: Callable, *args, **kwargs):
        if self._state == "open":
            time_since_failure = (
                datetime.now() - self._last_failure_time
                if self._last_failure_time
                else timedelta(0)
            )

            if time_since_failure > timedelta(seconds=self.recovery_timeout):
                self._state = "half-open"
                if self.logger:
                    self.logger.debug("Circuit breaker: open -> half-open")
            else:
                if self.logger:
                    remaining = self.recovery_timeout - time_since_failure.total_seconds()
                    self.logger.warning(
                        f"Circuit breaker OPEN. Recovery in {remaining:.1f}s"
                    )
                raise Exception(
                    f"Circuit breaker is OPEN (failures: {self._failure_count})"
                )

        try:
            result = await func(*args, **kwargs)

            # Успех - сбрасываем счетчики
            if self._state == "half-open":
                self._state = "closed"
                if self.logger:
                    self.logger.info("Circuit breaker: half-open -> closed")

            self._failure_count = 0
            return result

        except Exception as err:
            self._record_failure()
            raise

    def _record_failure(self):
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._failure_count >= self.failure_threshold and self._state != "open":
            old_state = self._state
            self._state = "open"
            if self.logger:
                self.logger.warning(
                    f"Circuit breaker: {old_state} -> open "
                    f"(failures: {self._failure_count}/{self.failure_threshold})"
                )

    def reset(self):
        self._failure_count = 0
        self._last_failure_time = None
        if self._state != "closed":
            old_state = self._state
            self._state = "closed"
            if self.logger:
                self.logger.info(f"Circuit breaker: {old_state} -> closed (manual reset)")


def should_retry(retry_state: RetryCallState) -> bool:
    if not retry_state.outcome.failed:
        return False

    exception = retry_state.outcome.exception()

    retryable_exceptions = (
        httpx.TimeoutException,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
        httpx.ConnectError,
        httpx.NetworkError,
        httpx.RemoteProtocolError,
        httpx.ProxyError,
        httpx.TransportError,
    )

    if isinstance(exception, retryable_exceptions):
        return True

    return False


class AsyncHTTPClient:
    def __init__(
        self,
        host: str,
        port: int,
        prefix: str = "",
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        use_tracing: bool = False,
        use_https: bool = False,
        use_http2: bool = False,
        timeout: float = 300.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        retry_attempts: int = 3,
        retry_min_wait: float = 0.1,
        retry_max_wait: float = 10.0,
        circuit_breaker_enabled: bool = False,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
        logger: Optional[interface.IOtelLogger] = None,
        log_context: Optional[ContextVar[dict]] = None,
    ):
        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}:{port}{prefix}"

        self.default_headers = headers or {}
        self.default_cookies = cookies or {}
        self.use_tracing = use_tracing
        self.logger = logger
        self.log_context = log_context

        # Retry параметры
        self.retry_attempts = retry_attempts
        self.retry_min_wait = retry_min_wait
        self.retry_max_wait = retry_max_wait

        # Circuit Breaker
        self.circuit_breaker: Optional[CircuitBreaker] = None
        if circuit_breaker_enabled:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                recovery_timeout=circuit_breaker_timeout,
                logger=logger,
            )

        self.session = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.default_headers,
            cookies=self.default_cookies,
            timeout=timeout,
            http2=use_http2,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
            follow_redirects=True,
        )

    async def close(self):
        if self.session and not self.session.is_closed:
            await self.session.aclose()
            if self.logger:
                self.logger.debug("HTTP client closed")

    async def __aenter__(self) -> "AsyncHTTPClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _prepare_headers(self, extra_headers: Optional[dict] = None) -> dict:
        headers = {**self.default_headers, **(extra_headers or {})}

        if self.log_context:
            try:
                headers.update(self.log_context.get())
            except LookupError:
                pass

        # Добавить tracing headers
        if self.use_tracing:
            propagate.inject(headers)

        return headers

    async def _execute_request(
        self, method: str, url: str, **kwargs
    ) -> httpx.Response:
        headers = self._prepare_headers(kwargs.pop("headers", None))
        cookies = {**self.default_cookies, **kwargs.pop("cookies", {})}

        async def _make_request():
            response = await self.session.request(
                method, url, headers=headers, cookies=cookies, **kwargs
            )
            response.raise_for_status()
            return response

        if self.circuit_breaker:
            return await self.circuit_breaker.call(_make_request)
        else:
            return await _make_request()

    async def _request_with_retry(
        self, method: str, url: str, **kwargs
    ) -> httpx.Response | None:
        if self.retry_attempts <= 1:
            return await self._execute_request(method, url, **kwargs)

        retry_strategy = AsyncRetrying(
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=self.retry_min_wait,
                max=self.retry_max_wait,
            ),
            retry=should_retry,
            reraise=True,
        )

        attempt_num = 0
        async for attempt in retry_strategy:
            with attempt:
                attempt_num = attempt.retry_state.attempt_number
                try:
                    response = await self._execute_request(method, url, **kwargs)

                    # Логировать если была не первая попытка
                    if attempt_num > 1 and self.logger:
                        self.logger.info(
                            f"Request {method} {url} succeeded after {attempt_num} attempts"
                        )

                    return response

                except Exception as err:
                    if self.logger and attempt_num < self.retry_attempts:
                        self.logger.warning(
                            f"Request {method} {url} failed (attempt {attempt_num}/{self.retry_attempts}): "
                            f"{err.__class__.__name__}: {str(err)}"
                        )
                    raise
        return None

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry("DELETE", url, **kwargs)

    def reset_circuit_breaker(self):
        if self.circuit_breaker:
            self.circuit_breaker.reset()

    @property
    def circuit_breaker_state(self) -> Optional[str]:
        return self.circuit_breaker.state if self.circuit_breaker else None