"""Explicit, bounded examples for one selected CAL Targum Hebrew reflex.

The CAL Onqelos and Neofiti pages expose the same MT / Targum paired
`div > span.heb` and `div > div > span.heb` structure. Do not infer verse
IDs, deduplicate examples, or walk the returned lexical link.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from cal_mcp.client import CalHttpClient, CalRequest, CalResponse
from cal_mcp.concordance import _validate_lemma_key
from cal_mcp.errors import CalInputError, CalParseError
from cal_mcp.targum import (
    TargumProvenance,
    _make_provenance,
    _provenance_to_dict,
    _validate_mt_lemma_id,
    _validate_targum,
)

_EXAMPLE_PATHS = {"onqelos": "getOMT.php", "neofiti": "getNMT.php"}
_SOURCE_HEADINGS = {"onqelos": "Onqelos", "neofiti": "Neofiti"}


class TargumReflexExamplesParseError(CalParseError):
    """The chosen CAL example page no longer expresses its claimed semantics."""


@dataclass(frozen=True, slots=True)
class TargumReflexExample:
    mt_text: str
    targum_text: str


@dataclass(frozen=True, slots=True)
class TargumReflexExamplesPage:
    source_label: str
    mt_hebrew_lemma: str
    lemma_key: str
    examples: tuple[TargumReflexExample, ...]


@dataclass(frozen=True, slots=True)
class TargumReflexExamplesResult:
    targum: str
    mt_lemma_id: str
    lemma_key: str
    source_label: str
    mt_hebrew_lemma: str
    examples: tuple[TargumReflexExample, ...]
    provenance: TargumProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "targum": self.targum,
            "mt_lemma_id": self.mt_lemma_id,
            "lemma_key": self.lemma_key,
            "source_label": self.source_label,
            "mt_hebrew_lemma": self.mt_hebrew_lemma,
            "examples": [
                {"mt_text": example.mt_text, "targum_text": example.targum_text}
                for example in self.examples
            ],
            "provenance": _provenance_to_dict(self.provenance),
        }


def _visible_lines(text: str) -> str:
    """Preserve actual CAL line breaks while folding incidental HTML whitespace."""
    return "\n".join(" ".join(line.split()) for line in text.split("\n") if line.strip())


class _ReflexExamplesParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[str] = []
        self._heading_parts: list[str] | None = None
        self._skip = 0
        self._div_depth = 0
        self._span_parts: list[str] | None = None
        self._span_role = 0
        self.spans: list[tuple[int, str]] = []
        self.anchor_href: str | None = None
        self.anchor_text: list[str] = []
        self.loose_parts: list[str] = []
        self._in_anchor = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("style", "script"):
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "h3":
            if self._heading_parts is not None or len(self.headings) >= 2:
                raise TargumReflexExamplesParseError("unexpected reflex-example heading")
            self._heading_parts = []
        elif tag == "a":
            if self._heading_parts is None or self.anchor_href is not None or self._in_anchor:
                raise TargumReflexExamplesParseError("unexpected reflex-example link")
            href = dict(attrs).get("href")
            if not href:
                raise TargumReflexExamplesParseError("missing reflex-example lemma link")
            self.anchor_href = href
            self._in_anchor = True
        elif tag == "div":
            if len(self.headings) == 2:
                self._div_depth += 1
                if self._div_depth > 2:
                    raise TargumReflexExamplesParseError("unexpected nested example wrapper")
        elif tag == "span" and len(self.headings) == 2:
            if self._span_parts is not None:
                raise TargumReflexExamplesParseError("nested reflex-example text spans")
            classes = (dict(attrs).get("class") or "").split()
            if classes != ["heb"] or self._div_depth not in (1, 2):
                raise TargumReflexExamplesParseError("unexpected reflex-example text span")
            self._span_parts = []
            self._span_role = self._div_depth
        elif tag == "br" and self._span_parts is not None:
            self._span_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script"):
            if self._skip:
                self._skip -= 1
            return
        if self._skip:
            return
        if tag == "a":
            self._in_anchor = False
        elif tag == "h3":
            if self._heading_parts is None:
                raise TargumReflexExamplesParseError("unmatched example heading")
            self.headings.append(" ".join("".join(self._heading_parts).split()))
            self._heading_parts = None
        elif tag == "span" and self._span_parts is not None:
            text = _visible_lines("".join(self._span_parts))
            if not text:
                raise TargumReflexExamplesParseError("empty reflex-example text span")
            self.spans.append((self._span_role, text))
            self._span_parts = None
            self._span_role = 0
        elif tag == "div" and len(self.headings) == 2:
            if not self._div_depth:
                raise TargumReflexExamplesParseError("unmatched example wrapper")
            self._div_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._in_anchor:
            self.anchor_text.append(data)
        if self._span_parts is not None:
            self._span_parts.append(data)
        elif self._heading_parts is None and len(self.headings) == 2 and data.strip():
            self.loose_parts.append(" ".join(data.split()))


def _check_origin_and_selectors(
    source_url: str, *, targum: str, mt_lemma_id: str, lemma_key: str
) -> None:
    try:
        url = urlsplit(source_url)
        port = url.port
    except ValueError as error:
        raise TargumReflexExamplesParseError("invalid CAL example source URL") from error
    query = parse_qs(url.query, keep_blank_values=True)
    if (
        url.scheme != "https"
        or url.hostname != "cal.huc.edu"
        or port is not None
        or url.username is not None
        or url.password is not None
        or url.fragment
        or url.path != "/" + _EXAMPLE_PATHS[targum]
        or set(query) != {"MT", "cal"}
        or query["MT"] != [mt_lemma_id]
        or query["cal"] != [lemma_key]
    ):
        raise TargumReflexExamplesParseError(
            "CAL reflex example source selectors contradict request"
        )


def _check_lexicon_link(href: str | None, label: str, lemma_key: str) -> None:
    if not href:
        raise TargumReflexExamplesParseError("missing CAL reflex example lemma link")
    target = urlsplit(href)
    query = parse_qs(target.query, keep_blank_values=True)
    if (
        (target.scheme or target.netloc)
        or target.path != "/oneentry.php"
        or target.fragment
        or set(query) != {"cits", "lemma"}
        or query["cits"] != ["all"]
        or query["lemma"] != [lemma_key]
        or label != lemma_key
    ):
        raise TargumReflexExamplesParseError("CAL reflex example lemma link contradicts request")


def parse_targum_reflex_examples_page(
    response: CalResponse, *, targum: str, mt_lemma_id: str, lemma_key: str
) -> TargumReflexExamplesPage:
    selected_targum = _validate_targum(targum)
    selected_id = _validate_mt_lemma_id(mt_lemma_id)
    _, _, selected_lemma = _validate_lemma_key(lemma_key)
    if lemma_key != selected_lemma:
        raise CalInputError("lemma_key must be canonical")
    _check_origin_and_selectors(
        response.url, targum=selected_targum, mt_lemma_id=selected_id, lemma_key=selected_lemma
    )
    parser = _ReflexExamplesParser()
    parser.feed(response.body.decode("utf-8", errors="replace"))
    parser.close()
    source = _SOURCE_HEADINGS[selected_targum]
    if len(parser.headings) != 2:
        raise TargumReflexExamplesParseError("CAL reflex example page lacks two source headings")
    prefix = f"{source} verses where MT "
    first, second = parser.headings
    if not first.startswith(prefix) or not first[len(prefix) :].strip():
        raise TargumReflexExamplesParseError("CAL reflex example MT heading contradicts source")
    if second != f"is rendered by Aramaic {selected_lemma}":
        raise TargumReflexExamplesParseError("CAL reflex example heading names another CAL lemma")
    _check_lexicon_link(
        parser.anchor_href, " ".join("".join(parser.anchor_text).split()), selected_lemma
    )
    if " ".join(parser.loose_parts) != "Click the Aramaic lemma to see the full entry":
        raise TargumReflexExamplesParseError("unrecognized text outside reflex example blocks")
    if (
        not parser.spans
        or len(parser.spans) % 2
        or parser._span_parts is not None
        or parser._div_depth
        or parser._heading_parts is not None
    ):
        raise TargumReflexExamplesParseError(
            "CAL reflex example lacks complete ordered MT/Aramaic pairs"
        )
    examples: list[TargumReflexExample] = []
    for i in range(0, len(parser.spans), 2):
        mt_depth, mt_text = parser.spans[i]
        targum_depth, targum_text = parser.spans[i + 1]
        if (mt_depth, targum_depth) != (1, 2):
            raise TargumReflexExamplesParseError("CAL reflex examples have wrong pairing structure")
        examples.append(TargumReflexExample(mt_text=mt_text, targum_text=targum_text))
    return TargumReflexExamplesPage(
        source_label=source,
        mt_hebrew_lemma=first[len(prefix) :],
        lemma_key=selected_lemma,
        examples=tuple(examples),
    )


class TargumReflexExamplesService:
    def __init__(self, client: CalHttpClient) -> None:
        self._client = client

    async def examples(
        self, targum: str, mt_lemma_id: str, lemma_key: str
    ) -> TargumReflexExamplesResult:
        selected_targum = _validate_targum(targum)
        selected_id = _validate_mt_lemma_id(mt_lemma_id)
        _, _, selected_lemma = _validate_lemma_key(lemma_key)
        if selected_lemma != lemma_key:
            raise CalInputError("lemma_key must be a canonical CAL lemma key")
        result = await self._client.fetch(
            CalRequest(
                method="GET",
                path=_EXAMPLE_PATHS[selected_targum],
                params=(("MT", selected_id), ("cal", selected_lemma)),
            ),
            parser=lambda response: parse_targum_reflex_examples_page(
                response,
                targum=selected_targum,
                mt_lemma_id=selected_id,
                lemma_key=selected_lemma,
            ),
            cache_namespace=f"targum-reflex-examples-{selected_targum}-v1",
        )
        page = result.value
        return TargumReflexExamplesResult(
            targum=selected_targum,
            mt_lemma_id=selected_id,
            lemma_key=selected_lemma,
            source_label=page.source_label,
            mt_hebrew_lemma=page.mt_hebrew_lemma,
            examples=page.examples,
            provenance=_make_provenance(
                result.source_url,
                result.retrieved_at,
                operation="targum_reflex_examples",
                targum=selected_targum,
                mt_lemma_id=selected_id,
                lemma_key=selected_lemma,
            ),
        )
