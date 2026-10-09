from __future__ import annotations

import importlib
import inspect
import pkgutil
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import pytest
from mcp import Client

import cal_mcp
import cal_mcp.server as server_module
from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.errors import CalParseError, PublicErrorKind, classify_public_tool_error

_UNRECOGNIZABLE_PAGE = b"<html><body><p>An unexpected CAL layout</p></body></html>"


def _parse_error_classes() -> list[type[BaseException]]:
    classes: dict[str, type[BaseException]] = {}
    for module_info in pkgutil.iter_modules(cal_mcp.__path__):
        module = importlib.import_module(f"cal_mcp.{module_info.name}")
        for name, value in inspect.getmembers(module, inspect.isclass):
            if name.endswith("ParseError") and issubclass(value, BaseException):
                classes[f"{value.__module__}.{value.__qualname__}"] = value
    return [classes[key] for key in sorted(classes)]


@pytest.mark.parametrize("error_class", _parse_error_classes(), ids=lambda cls: cls.__name__)
def test_every_parse_error_class_is_parser_drift(error_class: type[BaseException]) -> None:
    assert issubclass(error_class, CalParseError)
    classified = classify_public_tool_error("cal_tool", error_class("CAL layout changed"))
    assert classified is not None
    assert classified.kind is PublicErrorKind.PARSER_DRIFT


def _request_url(request: CalRequest) -> str:
    url = f"https://cal.huc.edu/{request.path.lstrip('/')}"
    if request.params:
        url = f"{url}?{urlencode(request.params)}"
    return url


# One representative tool per CAL-backed module, with arguments that pass local validation.
_TOOL_CASES: list[tuple[str, dict[str, Any]]] = [
    ("cal_lexicon_browse", {"prefix": "mlk"}),
    ("cal_lexicon_citation_context", {"full_coordinate": "31000424"}),
    ("cal_gloss_search", {"query": "camel"}),
    ("cal_text_page", {"file_id": "13250"}),
    ("cal_token_analysis", {"coordinate": "13250000010001", "word_index": 1}),
    ("cal_text_concordance", {"text_id": "13250"}),
    ("cal_bibliography_author", {"author": "Sokoloff"}),
    ("cal_targum_parallel", {"book": "Gen", "chapter": 1, "verse": 1}),
    ("cal_syriac_peshitta_parallel", {"book": "Gen", "chapter": 1, "verse": 1}),
    ("cal_external_citation_dialects", {}),
    ("cal_dictionary_collation", {"source": "djba", "page": "1"}),
]


@pytest.mark.anyio
@pytest.mark.parametrize(("tool", "arguments"), _TOOL_CASES, ids=[case[0] for case in _TOOL_CASES])
async def test_parser_drift_errors_carry_the_cal_source_url(
    monkeypatch: pytest.MonkeyPatch, tool: str, arguments: dict[str, Any]
) -> None:
    requested: list[str] = []

    async def transport(request: CalRequest, config: CalClientConfig) -> CalResponse:
        del config
        url = _request_url(request)
        requested.append(url)
        return CalResponse(
            status_code=200,
            url=url,
            body=_UNRECOGNIZABLE_PAGE,
            content_type="text/html; charset=UTF-8",
            retrieved_at=datetime(2026, 10, 9, tzinfo=UTC),
        )

    def client_factory() -> CalHttpClient:
        return CalHttpClient(
            config=CalClientConfig(max_retries=0, retry_backoff_seconds=0),
            transport=transport,
        )

    monkeypatch.setattr(server_module, "CalHttpClient", client_factory)
    async with Client(server_module.mcp, raise_exceptions=True) as client:
        result = await client.call_tool(tool, arguments)

    assert result.is_error is True
    assert result.structured_content is not None
    error = result.structured_content["error"]
    assert error["kind"] == "parser_drift", error
    assert requested
    assert error["source_url"] == requested[-1]
    assert error["upstream_reached"] is True


def test_untrusted_parse_error_url_is_not_published() -> None:
    error = CalParseError("CAL layout changed")
    error.url = "https://example.org/private?token=DO_NOT_LEAK"
    classified = classify_public_tool_error("cal_tool", error)
    assert classified is not None
    assert classified.source_url is None
    assert "DO_NOT_LEAK" not in classified.message


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tag", "shown"),
    [("yhwh", True), ("do_not_leak", False), ("abcdefghijklmnopq", False)],
)
async def test_text_row_error_shows_only_plain_tag_names(tag: str, shown: bool) -> None:
    from test_text_page_row_coordinates_current import SAMARITAN, _page

    from cal_mcp.texts import TextParseError

    body = SAMARITAN.read_text(encoding="utf-8")
    with pytest.raises(TextParseError) as exc_info:
        await _page(body.replace(">yhwh</a>", f"><{tag}>yhwh</a>", 1).encode(), "56000", "112")
    assert "unexpected" in str(exc_info.value)
    assert (tag in str(exc_info.value)) is shown
