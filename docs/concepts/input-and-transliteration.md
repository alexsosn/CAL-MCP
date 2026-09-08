# Input and transliteration

CAL-MCP keeps query normalization deterministic and intentionally narrow. CAL remains the authority for what a query means linguistically; the adapter does not guess roots, restore spellings, perform morphology, or ask an LLM to reinterpret input.

## Upstream representations

The current CAL lexicon browser documents four accepted input representations:

- CAL code;
- Unicode transliteration;
- Unicode Hebrew square script;
- Unicode Syriac.

CAL's general advantages page also confirms Roman transliteration, Unicode, Hebrew square script, and Syriac keyboard input. `normalize_query()` therefore prefers direct pass-through for representations that CAL already accepts. This query-normalization behavior is separate from the local `convert_to_cal_code()` / `cal_convert_to_code` capability described below: callers can explicitly request CAL Roman-code conversion without changing how ordinary upstream queries are normalized.

The upstream evidence was rechecked in September 2026:

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

Hebrew, Syriac, Imperial Aramaic, Palmyrene, Nabataean, Hatran, Samaritan, and Mandaic are detected by Unicode script/block. The dedicated-script converter validates against an explicit researched character table rather than accepting every code point merely because it lies in the same Unicode block. Mixing supported scripts in one conversion input is rejected rather than guessed.

The current automatic Unicode-transliteration alphabet is deliberately limited to the shared Roman consonants above plus the characters explicitly shown by CAL's current lexicon-browser table: `ˀ ˁ ḥ ṭ ṗ ṣ š ś`. Space and underscore are the locally supported separators. CAL's `@` connector is CAL code, not Unicode transliteration; the browser explicitly tells Unicode/browser users to enter a space for that case. Broader scholarly transliteration conventions are not inferred merely because CAL may display additional vocalized forms in results.

## CAL code and Unicode normalization

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

When a `normalize_query()` CAL-code query consists entirely of this documented simple subset, CAL-MCP converts it table-by-table to Unicode transliteration. Examples covered by tests:

```text
$)wl      -> šˀwl
br@mwt)   -> br mwtˀ
w_        -> w_
```

Because `@` converts to a space, connector-only values such as `@`, `@@`, or `@ @` are rejected after conversion instead of becoming blank upstream queries. Embedded connectors such as `br@mwt)` remain valid.

CAL's Roman-code documentation also defines Jewish Aramaic vocalization codes (`a A e E i u U o O :`), Syriac diacritic/punctuation codes, Mandaic `D H S`, and manuscript/editorial syntax. Those documented characters are accepted as explicit CAL code, but are not partially converted through the simple CAL-code-to-Unicode normalization table. For example, `mlk%` and `mAlk` remain CAL code and pass through unchanged.

The local CAL-code validator uses an explicit whitelist derived from those documented conventions rather than accepting every ASCII letter or punctuation mark.

## Local CAL-code converter

`convert_to_cal_code()` and the public local-only MCP tool `cal_convert_to_code` convert researched source representations into CAL Roman code. The converter performs zero CAL requests and is distinct from `normalize_query()` pass-through behavior.

The supported v0.1 source representations are:

- `unicode_transliteration`;
- `hebrew`;
- `syriac`, including ordinary Christian Palestinian Aramaic (CPA) Syriac-script input;
- `imperial_aramaic`;
- `palmyrene`;
- `nabataean`;
- `hatran`;
- `samaritan`;
- `mandaic`.

Explicit valid CAL code and plain shared Roman consonants pass through unchanged. The converter does not translate Hebrew into Syriac or Syriac into Hebrew; instead, each supported representation maps directly to CAL Roman code according to its researched table.

The result is structured per space-separated word. Each word has an ordered `candidates` collection and an `ambiguities` collection. A deterministic word has one candidate. A Unicode grapheme that genuinely lacks a CAL distinction returns every researched finite alternative rather than guessing from a dictionary, dialect, morphology, or context.

### Finite ambiguity

The known v0.1 finite ambiguities include:

- bare Hebrew `ש` -> `$` or `&`; explicit shin dot `שׁ` -> `$`, explicit sin dot `שׂ` -> `&`;
- Hatran `𐣣` (U+108E3 DALETH-RESH) -> `d` or `r`;
- Samaritan `ࠔ` (SHAN) -> `$` or `&` because the encoded grapheme does not distinguish CAL shin from sin;
- Syriac `ܖ` (U+0716 DOTLESS DALATH RISH) -> `d` or `r`.

Candidate ordering is stable. Expansion is bounded to **32 candidates per word**. If another ambiguous grapheme would exceed that limit, conversion fails explicitly before returning a partial result; CAL-MCP will never silently truncate a justified candidate set.

`cal_lexicon_lookup` can consume these finite candidates. It derives all complete candidates before network access, deduplicates equivalent CAL browser prefixes, permits at most eight unique prefix requests, and fetches at most one selected entry. See [Lexicon lookup and CAL-code conversion](../tools/lexicon.md) for the request-volume contract.

### Script-specific deterministic edges

The dedicated-script tables include distinctions that cannot be recovered safely from alphabet order alone:

- Syriac/CPA `ܧ` (REVERSED PE) -> CAL `P`; final semkath `ܤ` -> `s`;
- Mandaic `ࡇ` -> `H`, `ࡑ` -> `S`, and `ࡖ` -> `D`, preserving CAL's Mandaic-specific uppercase codes;
- Mandaic `ࡗ` (KAD) -> `kD` as a deterministic two-code expansion;
- Mandaic Unicode letters for vowel-bearing consonantal letters retain their researched CAL forms, including `ࡀ` -> `a`, `ࡅ` -> `u`, and `ࡉ` -> `i`.

These are explicit evidence-backed mappings, not generalized transliteration rules.

### Fail-closed boundary

The converter deliberately fails closed outside its researched tables. Unsupported vowels, combining marks, punctuation, editorial signs, numbers, block code points without verified letter identities, and mixed-script input are not silently stripped. In particular:

- Syriac `ܞ` (YUDH HE) remains **unsupported** because a direct current-CAL mapping for the single Unicode scalar has not been established;
- Mandaic `ࡘ` (borrowed AIN) remains unsupported pending a verified current-CAL Roman correspondence;
- Syriac, Hebrew, Samaritan, and Mandaic combining marks are unsupported unless a specific mapping has been researched and implemented;
- unverified punctuation and numeric signs in dedicated script blocks remain unsupported.

The converter never performs morphology, root inference, historical-spelling reconstruction, vowel restoration, or contextual disambiguation. Failure is preferable to producing a plausible but unjustified CAL spelling.

## Explicit representation override

Use an explicit override when the caller already knows the representation:

```python
from cal_mcp.normalization import InputRepresentation, normalize_query

query = normalize_query("$)wl", representation=InputRepresentation.CAL_CODE)
assert query.normalized == "šˀwl"
```

An override validates rather than coerces. Declaring `mlk` to be Hebrew, for example, raises `UnsupportedQueryError`; CAL-MCP will not translate it merely to satisfy the override. Declaring CAL-only `@` syntax as Unicode transliteration is likewise rejected.

The same principle applies to `convert_to_cal_code()`: choosing a representation does not authorize characters outside that representation's researched table.

## Query and form encoding

`encode_pairs()` performs standard UTF-8 form/query encoding while preserving input pair order and repeated keys. Raw plus signs, percent signs, ampersands, spaces, Hebrew, Syriac, and Unicode transliteration are encoded rather than interpolated into URLs manually.

```python
from cal_mcp.normalization import encode_pairs

encoded = encode_pairs((("lemma", "br mwtˀ"), ("q", "a+b%&")))
assert encoded == "lemma=br+mwt%CB%80&q=a%2Bb%25%26"
```

Endpoint adapters should continue to build typed `CalRequest` parameter/form pairs instead of concatenating URLs. The HTTP layer remains responsible for the actual CAL request boundary; this helper exists for deterministic encoding where an upstream form or test requires an encoded representation.

## Deliberate non-features

Normalization and conversion do not:

- infer a root from an inflected form;
- remove or add mater lectionis;
- normalize dialect spelling;
- fuzzy-correct typos;
- choose among finite candidates by lexical probability;
- invent support for unverified scholarly diacritics or script marks;
- infer CAL `@` merely from whitespace;
- perform network requests from the converter.

When future endpoint or corpus evidence justifies another deterministic or finitely ambiguous mapping, extend the research, table, and tests together rather than adding heuristic conversion.