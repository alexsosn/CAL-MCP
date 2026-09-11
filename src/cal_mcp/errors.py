from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cal_mcp.client import (
    CalContentError,
    CalNetworkError,
    CalRequestValidationError,
    CalResponseTooLargeError,
    CalUpstreamError,
)

_TRANSIENT_STATUS_CODES = frozenset({500, 502, 503, 504})
_MAX_PUBLIC_MESSAGE_CHARS = 500


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
        return PublicToolError(
            kind=PublicErrorKind.UPSTREAM_HTTP,
            operation=operation,
            upstream_reached=True,
            retryable=error.status_code in _TRANSIENT_STATUS_CODES,
            message=_safe_message(error),
            source_url=error.url,
            status_code=error.status_code,
        )
    if isinstance(error, CalResponseTooLargeError):
        return PublicToolError(
            kind=PublicErrorKind.RESPONSE_TOO_LARGE,
            operation=operation,
            upstream_reached=True,
            retryable=False,
            message=_safe_message(error),
            source_url=error.url,
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
            message=_safe_message(error),
        )
    return None


def _safe_message(error: BaseException) -> str:
    text = " ".join(str(error).split())
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
