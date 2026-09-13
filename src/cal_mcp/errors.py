from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from cal_mcp.client import (
    CalContentError,
    CalNetworkError,
    CalRequestValidationError,
    CalResponseTooLargeError,
    CalUpstreamError,
)

_TRANSIENT_STATUS_CODES = frozenset({500, 502, 503, 504})
_MAX_PUBLIC_MESSAGE_CHARS = 500
_UNEXPECTED_CONTENT_TYPE_PREFIX = "CAL returned unexpected content type "
_MAINTENANCE_PAGE_PREFIX = "CAL maintenance page returned"
_GENERIC_CONTENT_MESSAGE = "CAL response content was rejected as unsafe"


class CalInputError(ValueError):
    """Intentional caller-input failure safe to expose through the MCP boundary."""


class CalParseError(CalContentError):
    """Base class for fail-closed CAL semantic/parser drift."""


class PublicErrorKind(StrEnum):
    INVALID_INPUT = "invalid_input"
    NETWORK = "network"
    UPSTREAM_HTTP = "upstream_http"
    RESPONSE_TOO_LARGE = "response_too_large"
    CONTENT = "content"
    PARSER_DRIFT = "parser_drift"


@dataclass(frozen=True, slots=True)
class PublicToolError:
    kind: PublicErrorKind
    operation: str
    upstream_reached: bool | None
    retryable: bool
    message: str
    source_url: str | None = None
    status_code: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "error": {
                "kind": self.kind.value,
                "operation": self.operation,
                "upstream_reached": self.upstream_reached,
                "retryable": self.retryable,
                "message": self.message,
                "source_url": self.source_url,
                "status_code": self.status_code,
            }
        }


def classify_public_tool_error(operation: str, error: BaseException) -> PublicToolError | None:
    """Classify only explicitly allowlisted CAL-MCP failures for public serialization."""

    if isinstance(error, CalInputError):
        return PublicToolError(
            kind=PublicErrorKind.INVALID_INPUT,
            operation=operation,
            upstream_reached=False,
            retryable=False,
            message=_safe_message(error),
        )
    if isinstance(error, CalRequestValidationError):
        return PublicToolError(
            kind=PublicErrorKind.INVALID_INPUT,
            operation=operation,
            upstream_reached=False,
            retryable=False,
            message=_safe_message(error),
        )
    if isinstance(error, CalNetworkError):
        return PublicToolError(
            kind=PublicErrorKind.NETWORK,
            operation=operation,
            upstream_reached=None,
            retryable=True,
            message=_safe_message(error),
        )
    if isinstance(error, CalUpstreamError):
        source_url = _trusted_cal_url(error.url)
        message = f"CAL returned HTTP {error.status_code}"
        if source_url is not None:
            message = f"{message} for {source_url}"
        return PublicToolError(
            kind=PublicErrorKind.UPSTREAM_HTTP,
            operation=operation,
            upstream_reached=True,
            retryable=error.status_code in _TRANSIENT_STATUS_CODES,
            message=_safe_text(message),
            source_url=source_url,
            status_code=error.status_code,
        )
    if isinstance(error, CalResponseTooLargeError):
        source_url = _trusted_cal_url(error.url)
        message = f"CAL response exceeded configured {error.max_response_bytes}-byte limit"
        if source_url is not None:
            message = f"{message} for {source_url}"
        return PublicToolError(
            kind=PublicErrorKind.RESPONSE_TOO_LARGE,
            operation=operation,
            upstream_reached=True,
            retryable=False,
            message=_safe_text(message),
            source_url=source_url,
        )
    if isinstance(error, CalParseError):
        return PublicToolError(
            kind=PublicErrorKind.PARSER_DRIFT,
            operation=operation,
            upstream_reached=True,
            retryable=False,
            message=_safe_message(error),
        )
    if isinstance(error, CalContentError):
        return PublicToolError(
            kind=PublicErrorKind.CONTENT,
            operation=operation,
            upstream_reached=True,
            retryable=False,
            message=_safe_content_message(error),
        )
    return None


def _trusted_cal_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.hostname != "cal.huc.edu"
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        return None
    return value


def _safe_content_message(error: CalContentError) -> str:
    text = " ".join(str(error).split())
    if text.startswith(_UNEXPECTED_CONTENT_TYPE_PREFIX):
        diagnostic, separator, _url = text.partition(" for ")
        if separator and len(diagnostic) <= _MAX_PUBLIC_MESSAGE_CHARS:
            return diagnostic
    if text.startswith(_MAINTENANCE_PAGE_PREFIX):
        return "CAL returned a probable maintenance page"
    return _GENERIC_CONTENT_MESSAGE


def _safe_message(error: BaseException) -> str:
    return _safe_text(str(error))


def _safe_text(value: str) -> str:
    text = " ".join(value.split())
    if not text:
        return "CAL-MCP operation failed"
    return text[:_MAX_PUBLIC_MESSAGE_CHARS]


__all__ = [
    "CalInputError",
    "CalParseError",
    "PublicErrorKind",
    "PublicToolError",
    "classify_public_tool_error",
]
