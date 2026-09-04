from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import parse_qs, urljoin, urlsplit

from cal_mcp.client import CalContentError, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import _Line, _Link, _parse_lines

_ID_RE = re.compile(r"^\d+$")
_PAGE_MARKER_RE = re.compile(
    r"^Page\s+(?P<page>\d+)\s+of\s+(?P<count>\d+)\s+"
    r"\((?P<total>\d+)\s+lines total\)$",
    re.IGNORECASE,
)
_NO_LINES_RE = re.compile(r"\bNO LINES FOR\b.*\bARE CURRENTLY STORED\b", re.IGNORECASE)
_TEXT_SEARCH_MARKER = "cal search for texts like:"
_TEXT_SEARCH_EMPTY_MARKER = "there are no files associated with the search term"


class TextParseError(CalContentError):
    """Raised when a CAL text page no longer exposes the required semantics."""


class TextPageStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class TextRef:
    file_id: str
    subtext_id: str | None
    label: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class TextCategoryRef:
    category_id: str
    label: str


@dataclass(frozen=True, slots=True)
class TextToken:
    coordinate: str
    word_index: int
    text: str
    lexical_url: str


@dataclass(frozen=True, slots=True)
class TextLine:
    coordinate: str
    display_coordinate: str | None
    text: str
    tokens: tuple[TextToken, ...]
    comment_url: str | None


@dataclass(frozen=True, slots=True)
class TextPage:
    text: TextRef
    page: int
    page_count: int | None
    total_lines: int | None
    previous_page: int | None
    next_page: int | None
    lines: tuple[TextLine, ...]


@dataclass(frozen=True, slots=True)
class TextCataloguePage:
    categories: tuple[TextCategoryRef, ...]
    texts: tuple[TextRef, ...]


@dataclass(frozen=True, slots=True)
class TextSearchPage:
    matches: tuple[TextRef, ...]


@dataclass(frozen=True, slots=True)
class TextProvenance:
    source: str
    source_url: str
    retrieved_at: datetime
    operation: str
    upstream_id: str | None = None
    subtext_id: str | None = None
    category_id: str | None = None
    page: int | None = None
    original_query: str | None = None
    submitted_query: str | None = None


@dataclass(frozen=True, slots=True)
class TextCatalogueResult:
    categories: tuple[TextCategoryRef, ...]
    texts: tuple[TextRef, ...]
    provenance: TextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "categories": [_category_to_dict(item) for item in self.categories],
            "texts": [_text_ref_to_dict(item) for item in self.texts],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TextSearchResult:
    matches: tuple[TextRef, ...]
    provenance: TextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "matches": [_text_ref_to_dict(item) for item in self.matches],
            "provenance": _provenance_to_dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class TextPageResult:
    status: TextPageStatus
    page: TextPage | None
    provenance: TextProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "page": _text_page_to_dict(self.page) if self.page is not None else None,
            "provenance": _provenance_to_dict(self.provenance),
        }


def parse_text_catalogue_page(response: CalResponse) -> TextCataloguePage:
    categories: list[TextCategoryRef] = []
    texts: list[TextRef] = []

    for line in _parse_lines(response):
        for link in line.links:
            category = _category_from_link(link)
            if category is not None:
                categories.append(category)
                continue
            text = _text_ref_from_link(link)
            if text is not None:
                texts.append(text)

    if not categories and not texts:
        raise TextParseError("CAL text catalogue contains no recognizable category or text links")
    return TextCataloguePage(categories=tuple(categories), texts=tuple(texts))


def parse_text_search_page(response: CalResponse) -> TextSearchPage:
    lines = _parse_lines(response)
    page_text = " ".join(line.text for line in lines)
    lowered = page_text.lower()

    if _TEXT_SEARCH_EMPTY_MARKER in lowered:
        return TextSearchPage(matches=())
    if _TEXT_SEARCH_MARKER not in lowered:
        raise TextParseError("CAL text search page is missing its result marker")

    matches: list[TextRef] = []
    for line in lines:
        for link in line.links:
            if not _is_path(link.href, "get_a_chapter.php"):
                continue
            label, description = _search_label_and_description(line, link)
            text = _text_ref_from_link(link, label=label, description=description)
            if text is None:
                raise TextParseError("CAL text search result contains a malformed text link")
            matches.append(text)

    if not matches:
        raise TextParseError(
            "CAL text search page has neither results nor the explicit no-files marker"
        )
    return TextSearchPage(matches=tuple(matches))


def parse_text_page(
    response: CalResponse,
    *,
    requested_file_id: str,
    requested_subtext_id: str | None,
    requested_page: int | None = None,
) -> TextPage | None:
    lines = _parse_lines(response)
    page_text = " ".join(line.text for line in lines)
    if _NO_LINES_RE.search(page_text) is not None:
        return None

    text_ref = _page_text_ref(lines, requested_file_id, requested_subtext_id)
    page_number, page_count, total_lines = _page_metadata(lines)
    if requested_page is not None and page_number != requested_page:
        raise TextParseError("CAL text page number differs from the requested page")
    previous_page, next_page = _page_navigation(lines)
    text_lines = tuple(
        parsed for line in lines if (parsed := _parse_text_line(line, response.url)) is not None
    )
    if not text_lines:
        raise TextParseError("CAL text page contains no recognizable coordinate/token rows")

    return TextPage(
        text=text_ref,
        page=page_number,
        page_count=page_count,
        total_lines=total_lines,
        previous_page=previous_page,
        next_page=next_page,
        lines=text_lines,
    )


class TextService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def catalogue(self, *, category_id: str | None = None) -> TextCatalogueResult:
        normalized_category = (
            None if category_id is None else _validate_id(category_id, "category_id")
        )
        if normalized_category is None:
            request = CalRequest(method="GET", path="newtextmenu.html")
        else:
            request = CalRequest(
                method="GET",
                path="showsubtexts.php",
                params=(("subtext", normalized_category),),
            )

        result = await self._client.fetch(
            request,
            parser=parse_text_catalogue_page,
            cache_namespace="text-catalogue-v1",
        )
        return TextCatalogueResult(
            categories=result.value.categories,
            texts=result.value.texts,
            provenance=TextProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="catalogue",
                category_id=normalized_category,
            ),
        )

    async def search(self, query: str) -> TextSearchResult:
        submitted = _prepare_text_search_query(query)
        result = await self._client.fetch(
            CalRequest(
                method="POST",
                path="newsearchtxts.php",
                data=(("search", submitted),),
            ),
            parser=parse_text_search_page,
            cache_namespace="text-search-v1",
        )
        return TextSearchResult(
            matches=result.value.matches,
            provenance=TextProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="search",
                original_query=query,
                submitted_query=submitted,
            ),
        )

    async def page(
        self,
        file_id: str,
        *,
        subtext_id: str | None = None,
        page: int = 1,
    ) -> TextPageResult:
        normalized_file = _validate_id(file_id, "file_id")
        normalized_subtext = None if subtext_id is None else _validate_id(subtext_id, "subtext_id")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("page must be a positive integer")

        params: list[tuple[str, str]] = [("file", normalized_file)]
        if normalized_subtext is not None:
            params.append(("sub", normalized_subtext))
        params.append(("page", str(page - 1)))

        def parse_requested(response: CalResponse) -> TextPage | None:
            return parse_text_page(
                response,
                requested_file_id=normalized_file,
                requested_subtext_id=normalized_subtext,
                requested_page=page,
            )

        result = await self._client.fetch(
            CalRequest(method="GET", path="get_a_chapter.php", params=tuple(params)),
            parser=parse_requested,
            cache_namespace="text-page-v1",
        )
        status = TextPageStatus.FOUND if result.value is not None else TextPageStatus.NOT_FOUND
        return TextPageResult(
            status=status,
            page=result.value,
            provenance=TextProvenance(
                source="CAL",
                source_url=result.source_url,
                retrieved_at=result.retrieved_at,
                operation="page",
                upstream_id=normalized_file,
                subtext_id=normalized_subtext,
                page=page,
            ),
        )


def _validate_id(value: str, name: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a CAL decimal identifier")
    return value


def _parse_id(value: str, name: str) -> str:
    if _ID_RE.fullmatch(value) is None:
        raise TextParseError(f"CAL returned a non-decimal {name}")
    return value


def _prepare_text_search_query(value: str) -> str:
    trimmed = value.strip(" ")
    if not trimmed:
        raise ValueError("CAL text search query must not be empty")
    if any(char.isspace() and char != " " for char in trimmed):
        raise ValueError("CAL text search words must be separated by ASCII spaces")
    parts = [part for part in trimmed.split(" ") if part]
    if not parts:
        raise ValueError("CAL text search query must not be empty")
    return " ".join(parts)


def _category_from_link(link: _Link) -> TextCategoryRef | None:
    if not _is_path(link.href, "showsubtexts.php"):
        return None
    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    category_id = _single_query_value(query, "subtext", "category")
    _parse_id(category_id, "category_id")
    label = link.text.strip()
    if not label:
        raise TextParseError("CAL text catalogue category link has no label")
    return TextCategoryRef(category_id=category_id, label=label)


def _text_ref_from_link(
    link: _Link,
    *,
    label: str | None = None,
    description: str | None = None,
) -> TextRef | None:
    if not _is_path(link.href, "get_a_chapter.php"):
        return None
    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    file_id = _single_query_value(query, "file", "text")
    _parse_id(file_id, "file_id")

    subtext_id: str | None = None
    sub_values = query.get("sub")
    if sub_values is not None:
        if len(sub_values) != 1:
            raise TextParseError("CAL text link has repeated sub identifiers")
        if sub_values[0]:
            subtext_id = _parse_id(sub_values[0], "subtext_id")

    rendered_label = (label if label is not None else link.text).strip()
    if not rendered_label:
        raise TextParseError("CAL text link has no rendered label")
    return TextRef(
        file_id=file_id,
        subtext_id=subtext_id,
        label=rendered_label,
        description=description,
    )


def _search_label_and_description(line: _Line, link: _Link) -> tuple[str, str | None]:
    if not link.text or link.text not in line.text:
        raise TextParseError("CAL text search link is detached from its result row")
    remainder = line.text.split(link.text, 1)[1].strip()
    if not remainder.startswith(":"):
        raise TextParseError("CAL text search result row is missing the file/label separator")
    remainder = remainder[1:].strip()
    if not remainder:
        raise TextParseError("CAL text search result row has no text label")
    label, separator, description = remainder.partition(":")
    label = label.strip()
    if not label:
        raise TextParseError("CAL text search result row has an empty text label")
    rendered_description = description.strip() if separator and description.strip() else None
    return label, rendered_description


def _page_text_ref(
    lines: list[_Line],
    requested_file_id: str,
    requested_subtext_id: str | None,
) -> TextRef:
    for line in lines:
        for link in line.links:
            if not _is_path(link.href, "get_file_info.php"):
                continue
            query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
            file_id = _single_query_value(query, "coord", "file-info")
            _parse_id(file_id, "file_id")
            if file_id != requested_file_id:
                raise TextParseError(
                    "CAL text page file identifier differs from the requested file"
                )
            prefix, separator, label = link.text.partition(":")
            if not separator or prefix.strip() != file_id or not label.strip():
                raise TextParseError("CAL text page file-info label is malformed")
            return TextRef(
                file_id=file_id,
                subtext_id=requested_subtext_id,
                label=label.strip(),
            )
    raise TextParseError("CAL text page is missing its file-information link")


def _page_metadata(lines: list[_Line]) -> tuple[int, int | None, int | None]:
    found: tuple[int, int, int] | None = None
    for line in lines:
        match = _PAGE_MARKER_RE.fullmatch(line.text)
        if match is None:
            continue
        candidate = (
            int(match.group("page")),
            int(match.group("count")),
            int(match.group("total")),
        )
        if candidate[0] < 1 or candidate[1] < candidate[0]:
            raise TextParseError("CAL text page has invalid pagination metadata")
        if found is not None and found != candidate:
            raise TextParseError("CAL text page exposes conflicting pagination metadata")
        found = candidate
    if found is None:
        return 1, None, None
    return found


def _page_navigation(lines: list[_Line]) -> tuple[int | None, int | None]:
    previous: int | None = None
    next_page: int | None = None
    for line in lines:
        for link in line.links:
            if not _is_path(link.href, "get_a_chapter.php"):
                continue
            label = link.text.lower()
            if "previous page" not in label and "next page" not in label:
                continue
            query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
            upstream_page = _single_query_value(query, "page", "page-navigation")
            if not upstream_page.isdigit():
                raise TextParseError("CAL text page navigation has a nonnumeric page")
            public_page = int(upstream_page) + 1
            if "previous page" in label:
                previous = _same_or_unset(previous, public_page, "previous")
            if "next page" in label:
                next_page = _same_or_unset(next_page, public_page, "next")
    return previous, next_page


def _parse_text_line(line: _Line, source_url: str) -> TextLine | None:
    tokens = tuple(
        token for link in line.links if (token := _token_from_link(link, source_url)) is not None
    )
    if not tokens:
        return None

    coordinate = tokens[0].coordinate
    if any(token.coordinate != coordinate for token in tokens):
        raise TextParseError("CAL text row mixes multiple machine coordinates")

    comment_link = _matching_comment_link(line.links, coordinate)
    if comment_link is not None:
        display_coordinate = comment_link.text.strip() or None
        if display_coordinate is None or not line.text.startswith(display_coordinate):
            raise TextParseError("CAL text row comment coordinate is detached from its text")
        rendered_text = line.text[len(display_coordinate) :].strip()
        comment_url = urljoin(source_url, comment_link.href)
    else:
        first_token_text = tokens[0].text
        token_position = line.text.find(first_token_text)
        if token_position < 0:
            raise TextParseError("CAL text row token is detached from its rendered text")
        display_coordinate = line.text[:token_position].strip() or None
        rendered_text = line.text[token_position:].strip()
        comment_url = None

    if not rendered_text:
        raise TextParseError("CAL text row has no rendered text after its coordinate")
    return TextLine(
        coordinate=coordinate,
        display_coordinate=display_coordinate,
        text=rendered_text,
        tokens=tokens,
        comment_url=comment_url,
    )


def _token_from_link(link: _Link, source_url: str) -> TextToken | None:
    if not _is_path(link.href, "bablex.php"):
        return None
    query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
    coordinate = _single_query_value(query, "coord", "token")
    word = _single_query_value(query, "word", "token")
    _parse_id(coordinate, "coordinate")
    if not word.isdigit():
        raise TextParseError("CAL lexical token link has a nonnumeric word index")
    text = link.text.strip()
    if not text:
        raise TextParseError("CAL lexical token link has no rendered token")
    return TextToken(
        coordinate=coordinate,
        word_index=int(word),
        text=text,
        lexical_url=urljoin(source_url, link.href),
    )


def _matching_comment_link(links: tuple[_Link, ...], coordinate: str) -> _Link | None:
    found: _Link | None = None
    for link in links:
        if not _is_path(link.href, "comment.php"):
            continue
        query = parse_qs(urlsplit(link.href).query, keep_blank_values=True)
        comment_coordinate = _single_query_value(query, "coord", "comment")
        _parse_id(comment_coordinate, "coordinate")
        if comment_coordinate != coordinate:
            raise TextParseError("CAL text row comment coordinate differs from token coordinate")
        if found is not None and found != link:
            raise TextParseError("CAL text row exposes multiple different comment links")
        found = link
    return found


def _single_query_value(
    query: dict[str, list[str]],
    key: str,
    context: str,
) -> str:
    values = query.get(key)
    if values is None or len(values) != 1 or not values[0]:
        raise TextParseError(f"CAL {context} link is missing a single {key} value")
    return values[0]


def _same_or_unset(current: int | None, value: int, direction: str) -> int:
    if current is not None and current != value:
        raise TextParseError(f"CAL text page exposes conflicting {direction}-page links")
    return value


def _is_path(href: str, filename: str) -> bool:
    return urlsplit(href).path.endswith(filename)


def _text_ref_to_dict(text: TextRef) -> dict[str, object]:
    return {
        "file_id": text.file_id,
        "subtext_id": text.subtext_id,
        "label": text.label,
        "description": text.description,
    }


def _category_to_dict(category: TextCategoryRef) -> dict[str, object]:
    return {"category_id": category.category_id, "label": category.label}


def _token_to_dict(token: TextToken) -> dict[str, object]:
    return {
        "coordinate": token.coordinate,
        "word_index": token.word_index,
        "text": token.text,
        "lexical_url": token.lexical_url,
    }


def _line_to_dict(line: TextLine) -> dict[str, object]:
    return {
        "coordinate": line.coordinate,
        "display_coordinate": line.display_coordinate,
        "text": line.text,
        "tokens": [_token_to_dict(item) for item in line.tokens],
        "comment_url": line.comment_url,
    }


def _text_page_to_dict(page: TextPage) -> dict[str, object]:
    return {
        "text": _text_ref_to_dict(page.text),
        "page": page.page,
        "page_count": page.page_count,
        "total_lines": page.total_lines,
        "previous_page": page.previous_page,
        "next_page": page.next_page,
        "lines": [_line_to_dict(item) for item in page.lines],
    }


def _provenance_to_dict(provenance: TextProvenance) -> dict[str, object]:
    return {
        "source": provenance.source,
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "operation": provenance.operation,
        "upstream_id": provenance.upstream_id,
        "subtext_id": provenance.subtext_id,
        "category_id": provenance.category_id,
        "page": provenance.page,
        "original_query": provenance.original_query,
        "submitted_query": provenance.submitted_query,
    }


__all__ = [
    "TextCataloguePage",
    "TextCatalogueResult",
    "TextCategoryRef",
    "TextLine",
    "TextPage",
    "TextPageResult",
    "TextPageStatus",
    "TextParseError",
    "TextProvenance",
    "TextRef",
    "TextSearchPage",
    "TextSearchResult",
    "TextService",
    "TextToken",
    "parse_text_catalogue_page",
    "parse_text_page",
    "parse_text_search_page",
]