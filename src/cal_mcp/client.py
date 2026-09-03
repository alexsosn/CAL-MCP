from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar, cast
from urllib.parse import urlencode, urljoin, urlsplit

import httpx2

from cal_mcp import __version__
from cal_mcp.request_policy import CacheRecord, MemoryResponseCache

T = TypeVar("T")

CAL_BASE_URL = "https://cal.huc.edu/"
_TRANSIENT_STATUS_CODES = frozenset({500, 502, 503, 504})
_HTML_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})


class CalClientError(RuntimeError):
    """Base class for CAL HTTP adapter failures."""


class CalRequestValidationError(CalClientError):
    """Raised before transport when a request is outside the CAL boundary."""


class CalNetworkError(CalClientError):
    """Raised when a bounded network/timeout retry budget is exhausted."""


class CalUpstreamError(CalClientError):
    """Raised for non-successful CAL HTTP responses."""

    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"CAL returned HTTP {status_code} for {url}")


class CalContentError(CalClientError):
    """Raised when a successful HTTP response is unsafe to parse as CAL HTML."""


@dataclass(frozen=True, slots=True)
class CalRequest:
    method: str
    path: str
    params: tuple[tuple[str, str], ...] = ()
    data: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class CalResponse:
    status_code: int
    url: str
    body: bytes
    content_type: str | None
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class CalFetchResult(Generic[T]):
    value: T
    source_url: str
    retrieved_at: datetime
    cache_hit: bool
    cache_age_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class CalClientConfig:
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 10.0
    total_timeout_seconds: float = 15.0
    max_concurrency: int = 2
    max_retries: int = 1
    retry_backoff_seconds: float = 0.25
    cache_enabled: bool = True
    cache_max_entries: int = 128
    cache_ttl_seconds: float = 900.0
    user_agent: str = f"CAL-MCP/{__version__} (+https://github.com/alexsosn/CAL-MCP)"

    def __post_init__(self) -> None:
        for name, value in (
            ("connect_timeout_seconds", self.connect_timeout_seconds),
            ("read_timeout_seconds", self.read_timeout_seconds),
            ("total_timeout_seconds", self.total_timeout_seconds),
            ("cache_ttl_seconds", self.cache_ttl_seconds),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and > 0")

        if not math.isfinite(self.retry_backoff_seconds) or self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be finite and >= 0")
        if not 1 <= self.max_concurrency <= 8:
            raise ValueError("max_concurrency must be between 1 and 8")
        if not 0 <= self.max_retries <= 3:
            raise ValueError("max_retries must be between 0 and 3")
        if not 0 <= self.cache_max_entries <= 4096:
            raise ValueError("cache_max_entries must be between 0 and 4096")
        if self.cache_ttl_seconds > 86400:
            raise ValueError("cache_ttl_seconds must not exceed 86400")
        if not self.user_agent.strip():
            raise ValueError("user_agent must not be empty")


Transport = Callable[[CalRequest, CalClientConfig], Awaitable[CalResponse]]


class _Httpx2Transport:
    def __init__(self, config: CalClientConfig) -> None:
        timeout = httpx2.Timeout(
            config.read_timeout_seconds,
            connect=config.connect_timeout_seconds,
            read=config.read_timeout_seconds,
        )
        limits = httpx2.Limits(
            max_connections=config.max_concurrency,
            max_keepalive_connections=config.max_concurrency,
        )
        self._client = httpx2.AsyncClient(
            timeout=timeout,
            limits=limits,
            headers={"User-Agent": config.user_agent},
            follow_redirects=False,
        )

    async def __call__(self, request: CalRequest, config: CalClientConfig) -> CalResponse:
        url = urljoin(CAL_BASE_URL, request.path.lstrip("/"))
        form_content = urlencode(request.data).encode("utf-8") if request.data else None
        headers = {"Content-Type": "application/x-www-form-urlencoded"} if request.data else None
        response = await self._client.request(
            request.method.upper(),
            url,
            params=list(request.params),
            content=form_content,
            headers=headers,
        )
        return CalResponse(
            status_code=response.status_code,
            url=str(response.url),
            body=response.content,
            content_type=response.headers.get("content-type"),
            retrieved_at=datetime.now(UTC),
        )

    async def aclose(self) -> None:
        await self._client.aclose()


class CalHttpClient:
    """Single bounded HTTP path for all CAL adapters.

    Endpoint parsers are injected into ``fetch``. Only a successful, validated,
    successfully parsed result is eligible for the process-local cache.
    """

    def __init__(
        self,
        *,
        config: CalClientConfig | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.config = config or CalClientConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        cache_entries = self.config.cache_max_entries if self.config.cache_enabled else 0
        self._cache: MemoryResponseCache[Any] = MemoryResponseCache(
            max_entries=cache_entries,
            ttl_seconds=self.config.cache_ttl_seconds,
        )
        self._transport_owner: _Httpx2Transport | None = None
        if transport is None:
            self._transport_owner = _Httpx2Transport(self.config)
            self._transport: Transport = self._transport_owner
        else:
            self._transport = transport

    async def __aenter__(self) -> CalHttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        del exc_type, exc, traceback
        await self.aclose()

    async def aclose(self) -> None:
        if self._transport_owner is not None:
            await self._transport_owner.aclose()

    async def fetch(
        self,
        request: CalRequest,
        *,
        parser: Callable[[CalResponse], T],
        cache_namespace: str,
    ) -> CalFetchResult[T]:
        normalized = self._validate_and_normalize_request(request)
        if not cache_namespace.strip():
            raise CalRequestValidationError("cache_namespace must not be empty")
        key = self._cache_key(cache_namespace, normalized)

        cached = self._cache.get(key)
        if cached is not None:
            record = cached.record
            return CalFetchResult(
                value=cast(T, record.value),
                source_url=record.source_url,
                retrieved_at=record.retrieved_at,
                cache_hit=True,
                cache_age_seconds=cached.age_seconds,
            )

        response = await self._request_with_retries(normalized)
        self._validate_content(response)
        parsed = parser(response)

        self._cache.put(
            key,
            CacheRecord(
                value=parsed,
                source_url=response.url,
                retrieved_at=response.retrieved_at,
            ),
        )
        return CalFetchResult(
            value=parsed,
            source_url=response.url,
            retrieved_at=response.retrieved_at,
            cache_hit=False,
        )

    def _validate_and_normalize_request(self, request: CalRequest) -> CalRequest:
        method = request.method.upper().strip()
        if method not in {"GET", "POST"}:
            raise CalRequestValidationError("CAL requests must use GET or POST")
        if not request.path.strip():
            raise CalRequestValidationError("CAL request path must not be empty")

        parsed = urlsplit(request.path)
        if parsed.scheme or parsed.netloc:
            raise CalRequestValidationError("CAL request path must be relative to cal.huc.edu")
        if parsed.query or parsed.fragment:
            raise CalRequestValidationError(
                "query parameters must be supplied via CalRequest.params"
            )

        path = parsed.path.lstrip("/")
        if not path or path == ".." or path.startswith("../") or "/../" in path:
            raise CalRequestValidationError("CAL request path must stay within the CAL site")

        return CalRequest(method=method, path=path, params=request.params, data=request.data)

    def _cache_key(self, namespace: str, request: CalRequest) -> str:
        return repr((namespace, request.method, request.path, request.params, request.data))

    async def _request_with_retries(self, request: CalRequest) -> CalResponse:
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self._request_once(request)
            except (TimeoutError, OSError, httpx2.HTTPError) as exc:
                if attempt >= self.config.max_retries:
                    if isinstance(exc, TimeoutError):
                        raise CalNetworkError("CAL request timeout") from exc
                    raise CalNetworkError("CAL network request failed") from exc
                await self._backoff(attempt)
                continue

            if response.status_code in _TRANSIENT_STATUS_CODES:
                if attempt < self.config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise CalUpstreamError(response.status_code, response.url)
            if response.status_code >= 300:
                raise CalUpstreamError(response.status_code, response.url)
            return response

        raise AssertionError("bounded retry loop exhausted unexpectedly")

    async def _request_once(self, request: CalRequest) -> CalResponse:
        async with self._semaphore:
            try:
                async with asyncio.timeout(self.config.total_timeout_seconds):
                    return await self._transport(request, self.config)
            except TimeoutError:
                raise

    async def _backoff(self, attempt: int) -> None:
        delay = self.config.retry_backoff_seconds * (2**attempt)
        if delay > 0:
            await asyncio.sleep(delay)

    def _validate_content(self, response: CalResponse) -> None:
        media_type = (response.content_type or "").split(";", 1)[0].strip().lower()
        if media_type not in _HTML_CONTENT_TYPES:
            raise CalContentError(
                f"CAL returned unexpected content type {response.content_type!r} for {response.url}"
            )

        prefix = response.body[:8192].decode("utf-8", errors="ignore").lower()
        if "<title>maintenance" in prefix or "<title>service unavailable" in prefix:
            raise CalContentError(f"CAL maintenance page returned for {response.url}")
