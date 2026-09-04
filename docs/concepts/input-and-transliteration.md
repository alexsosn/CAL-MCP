# Input and transliteration

CAL-MCP keeps query normalization deterministic and intentionally narrow. CAL remains the authority for what a query means linguistically; the adapter does not guess roots, restore spellings, perform morphology, or ask an LLM to reinterpret input.

## Upstream representations

The current CAL lexicon browser documents four accepted input representations:

- CAL code;
- Unicode transliteration;
- Unicode Hebrew square script;
- Unicode Syriac.

CAL's general advantages page also confirms Roman transliteration, Unicode, Hebrew square script, and Syriac keyboard input. CAL-MCP therefore prefers direct pass-through for representations CAL already accepts instead of converting Hebrew or Syriac locally.

The upstream evidence was rechecked on 2026-09-04:

- `https://cal.huc.edu/searching/fullbrowser.html`
- `https://cal.huc.edu/advantages.htm`
- `https://cal.huc.edu/prova.html`

## NormalizedQuery

`normalize_query()` returns a `NormalizedQuery` containing:

- `original` — the caller's string exactly as supplied;
- `normalized` — the value suitable for later endpoint-specific request construction;
- `representation` — the detected or explicitly selected input representation;
- `strategy` — whether the value passed through or used the limited CAL-code conversion table.

Ordinary ASCII spaces at the start/end are removed from `normalized`, while `original` remains unchanged. Internal ASCII spaces are preserved because CAL uses spaces in compounds and they can be semantically meaningful. Other Unicode whitespace such as NBSP is not silently stripped; unsupported whitespace is rejected. Control/surrogate characters are rejected. The normalized result is checked again after conversion so a non-empty source string cannot turn into a blank upstream query.

```python
from cal_mcp.normalization import normalize_query

query = normalize_query("  mlk  ")
assert query.original == "  mlk  "
assert query.normalized == "mlk"
assert query.representation == "roman_shared"
```

## Automatic detection

Automatic detection does not pretend that plain Roman input contains information that is not there.

`mlk`, for example, is compatible with both the CAL-code and Unicode-transliteration alphabets because those characters are identical in both. CAL-MCP reports such input as `roman_shared` and leaves it unchanged. The shared Roman consonant set is the intersection explicitly evidenced by the current CAL browser table: `b g d h w z y k l m n s p q r t`. Callers that need a particular interpretation can provide an explicit `InputRepresentation` override.

CAL-code-specific characters disambiguate the representation. For example, `x`, `T`, `P`, `c`, `$`, `&`, `)`, `(`, CAL vocalization codes such as `A`, and documented CAL punctuation are classified as CAL code. Arbitrary ASCII letters are not accepted merely because they are ASCII; undocumented examples such as `J`, `B`, and `j` are rejected.

Hebrew and Syriac are detected by script. A valid script input must contain at least one Unicode letter in the relevant script; an isolated Hebrew/Syriac combining mark or punctuation code point is not accepted as a query. Marks and punctuation from the same Unicode block may accompany a real script letter. Mixing Hebrew and Syriac in one query is rejected as ambiguous.

The current automatic Unicode-transliteration alphabet is deliberately limited to the shared Roman consonants above plus the characters explicitly shown by CAL's current lexicon-browser table: `ˀ ˁ ḥ ṭ ṗ ṣ š ś`. Space and underscore are the locally supported separators. CAL's `@` connector is CAL code, not Unicode transliteration; the browser explicitly tells Unicode/browser users to enter a space for that case. Broader scholarly transliteration conventions are not inferred merely because CAL may display additional vocalized forms in results.

## CAL code conversion

CAL's current lexicon browser publishes this simple consonantal correspondence:

| CAL code | Unicode |
| --- | --- |
| `)` | `ˀ` |
| `b` | `b` |
| `g` | `g` |
| `d` | `d` |
| `h` | `h` |
| `w` | `w` |
| `z` | `z` |
| `x` | `ḥ` |
| `T` | `ṭ` |
| `y` | `y` |
| `k` | `k` |
| `l` | `l` |
| `m` | `m` |
| `n` | `n` |
| `s` | `s` |
| `(` | `ˁ` |
| `p` | `p` |
| `P` | `ṗ` |
| `c` | `ṣ` |
| `q` | `q` |
| `r` | `r` |
| `$` | `š` |
| `&` | `ś` |
| `t` | `t` |
| `@` | space |
| `_` | `_` |

When a CAL-code query consists entirely of this documented simple subset, CAL-MCP converts it table-by-table to Unicode transliteration. Examples covered by tests:

```text
$)wl      -> šˀwl
br@mwt)   -> br mwtˀ
w_        -> w_
```

Because `@` converts to a space, connector-only values such as `@`, `@@`, or `@ @` are rejected after conversion instead of becoming blank upstream queries. Embedded connectors such as `br@mwt)` remain valid.

CAL's Roman-code documentation also defines Jewish Aramaic vocalization codes (`a A e E i u U o O :`), Syriac diacritic/punctuation codes, Mandaic `D H S`, and manuscript/editorial syntax. Those documented characters are accepted as CAL code, but are not partially converted through the simple consonant table. For example, `mlk%` and `mAlk` remain CAL code and pass through unchanged.

The local CAL-code validator uses an explicit whitelist derived from those documented conventions rather than accepting every ASCII letter or punctuation mark.

## No Hebrew/Syriac cross-conversion

CAL-MCP does not transliterate Hebrew to Syriac, Syriac to Hebrew, or either script to Roman code in v0.1. CAL's own browser table is not bijective across those scripts: some CAL distinctions have no direct Hebrew or Syriac cell. A local cross-script converter would therefore need additional linguistic or orthographic choices that are outside this ticket.

Users may submit Hebrew or Syriac directly because CAL accepts both.

## Explicit representation override

Use an explicit override when the caller already knows the representation:

```python
from cal_mcp.normalization import InputRepresentation, normalize_query

query = normalize_query("$)wl", representation=InputRepresentation.CAL_CODE)
assert query.normalized == "šˀwl"
```

An override validates rather than coerces. Declaring `mlk` to be Hebrew, for example, raises `UnsupportedQueryError`; CAL-MCP will not translate it merely to satisfy the override. Declaring CAL-only `@` syntax as Unicode transliteration is likewise rejected.

## Query and form encoding

`encode_pairs()` performs standard UTF-8 form/query encoding while preserving input pair order and repeated keys. Raw plus signs, percent signs, ampersands, spaces, Hebrew, Syriac, and Unicode transliteration are encoded rather than interpolated into URLs manually.

```python
from cal_mcp.normalization import encode_pairs

encoded = encode_pairs((("lemma", "br mwtˀ"), ("q", "a+b%&")))
assert encoded == "lemma=br+mwt%CB%80&q=a%2Bb%25%26"
```

Endpoint adapters should continue to build typed `CalRequest` parameter/form pairs instead of concatenating URLs. The HTTP layer remains responsible for the actual CAL request boundary; this helper exists for deterministic encoding where an upstream form or test requires an encoded representation.

## Deliberate non-features

Normalization does not:

- infer a root from an inflected form;
- remove or add mater lectionis;
- normalize dialect spelling;
- fuzzy-correct typos;
- choose among possible Hebrew/Syriac transliterations;
- invent support for unverified scholarly diacritics;
- perform network requests.

When future endpoint evidence justifies another deterministic mapping, extend the whitelist/table and its tests together rather than adding heuristic conversion.
