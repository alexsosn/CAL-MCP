# Issue #247 research — followable Hebrew-reflex examples

Date: 2026-10-10. Parent issue #109, focused implementation issue #247.

## Existing executable evidence

The public `cal_targum_hebrew_reflexes(targum, mt_lemma_id)` result contains:
`targum`, `mt_lemma_id`, `mt_hebrew_lemma`, and ordered `reflexes` with
`lemma_key`, `frequency`, `label`, `example_url`. The links are
validated in `_validated_reflex_url` before release. Their exact two query
controls are `MT` (parent's opaque decimal lemma ID) and `cal` (the
canonical CAL lemma key). The route is `getOMT.php` for `onqelos`, or
`getNMT.php` for `neofiti`. No arbitrary endpoint or URL execution is
needed. Parent handler `hebrew_reflexes` makes one POST and never follows a
reflex link.

The fixture `tests/fixtures/cal/targum_reflex_onqelos_1751_current.html`
returns `MT=1751&cal=tyq%232+N` in its one row. Neofiti fixture
`tests/fixtures/cal/targum_reflex_neofiti_1751.html` returns
`MT=1751&cal=gypwp+N` and another `syyg N` row. The existing ref
parser preserves those exact link semantics and already rejects mismatched
source IDs, invalid lemma keys, duplicate links and cross-origin URLs.

## Bounded current upstream research

- Two GETs in [run 38059457264](https://github.com/alexsosn/CAL-MCP/actions/runs/38059457264)
  (one concordance/one Onqelos). Both returned HTTP 200; Onqelos
  `getOMT.php?MT=1751&cal=tyq%232+N` was 4195 bytes, text/html.
- Two follow-up GETs in [run 38059641146](https://github.com/alexsosn/CAL-MCP/actions/runs/38059641146)
  were necessary to inspect DOM boundaries rather than rely on tag counts.
  Onqelos page has **two separate `h3` headings** stating the MT lemma
  and selected CAL reflex lemma. The second heading contains a
  `oneentry.php` link to that exact reflex. Ordered verse blocks are
  nested `div` / `span.heb`; MT and Aramaic text appear consecutively,
  with explicit biblical reference in the MT context. The probe displays
  repeated Deut 22:8 blocks, demonstrating that a parser must not infer
  a unique-verse set or deduplicate by scripture reference.
- Both probes were fixed, no redirects, with hard response-size cap;
  action triggers removed. No archive/corpus content was checked into Git.
- The one-request Neofiti `getNMT.php?MT=1751&cal=gypwp+N` structure
  audit [run 38059821947](https://github.com/alexsosn/CAL-MCP/actions/runs/38059821947)
  completed **HTTP 200** / 2973 bytes. It also displays two `h3`
  headings (Neofiti MT lemma, selected CAL reflex link) and one paired
  outer `div` containing Hebrew MT `span.heb` and a nested Aramaic
  `div/span.heb`. It showed one concrete Deut 22:8 example.
  The structural shape is shared across the two verified sources; their
  route identities and source-label semantics remain distinct.
  Its temporary workflow was removed; it did not fetch link targets.

## Proposed faithful contract

A new *explicit*, caller-controlled MCP operation:
`cal_targum_reflex_examples(targum, mt_lemma_id, lemma_key)`.
Accept only `onqelos`/`neofiti`, the exact already-returned opaque MT ID,
and the canonical already-returned CAL lemma key. Reconstruct the fixed
allowed GET with ordered exact `MT` and `cal` query values; do not expose
generic `url`, `path`, or `query` inputs.

Return structured provenance (`operation`, `targum`, `mt_lemma_id`,
`lemma_key`, exact CAL source URL, retrieval timestamp), source label and
ordered parallel MT/Aramaic snippets with the CAL-rendered passage reference
if explicitly present. **Do not infer verse alignment from ungrounded
repeated text.** Preserve duplicate examples in CAL order. If source
provides only opaque context blocks, represent ordered raw blocks with
kind/style rather than forging pairs.

Reject mismatched source/reflex headings, malformed/non-unique links,
missing examples or unauthorized external navigation as parser drift.
Treat a true explicitly marked CAL empty result separately, not as drift;
do not invent an empty marker without real evidence.

Neofiti is not assumed to share Onqelos markup before the bounded
current-source result is available. The two route families in #109 are
separate tasks: concordance KWIC with target coordinates (#246) has a
different document structure.

## Risk / user impact

The new operation adds one public tool to the current 34-tool pre-release
manifest. Update the explicit tool-count and release artifact assertions
if implemented, but do not silently change or weaken any existing tools.
One selected operation performs one GET, no sibling-reflex prefetch,
no chapter walk, no extra citation requests, no content mirror.


## 2026-10-10 live-acceptance discrepancy: sibling blocks, not nested blocks

One-time installed-wheel acceptance [38061551966](https://github.com/alexsosn/CAL-MCP/actions/runs/38061551966)
performed **exactly two actual CAL transports** (no retries), one Onqelos and
one Neofiti. Both real tool results returned typed `parser_drift`,
`CAL reflex examples have wrong pairing structure`; the driver blocked
release. Earlier simplified DOM-path instrumentation *appeared* to show
nested divs because the diagnostic's own pseudo-stack did not handle
HTML void `br` tags accurately. The reduced tests consequently embedded
the wrong nesting. This is a **fixture defect**, not evidence of live CAL
drift.

An additional **explicitly authorized** two-GET tag-only diagnostic
[38061662651](https://github.com/alexsosn/CAL-MCP/actions/runs/38061662651)
observed actual start/end tags and text *lengths only* (no verse content),
with redirects disabled and 256-KiB response caps; both HTTP 200.
The structural facts are:

- Onqelos: first example `<div><span class="heb">MT…</span></div>`,
  `<br>`, then **sibling** `<div><span class="heb">Aramaic…</span></div>`,
  `<hr>`; the exact pair repeats once, then a trailing `<hr>`.
  Each span has div depth **1**, not depths 1/2. Four blocks,
  two complete pairs, separators after blocks 2 and 4.
- Neofiti: the same sibling structure for one MT/Aramaic pair, with a
  terminating `<hr>` and one trailing `<hr>`. Two blocks at depth 1.
- No nested verse div appears on either sampled source. Hence
  rejecting unexpected depth-2 nesting is *required* in the observed
  current contract; simply accepting either depth is insufficiently strict.
- The selected reflex identity headings and exact returned `oneentry.php`
  link remain independently checked. The script must reject incomplete
  pairs, additional visible content, and mismatched CAL source selectors.
- Correct implementation models a sequence of **sibling one-span blocks**
  grouped **two per example**, with `<hr>` separation after each pair.
  A trailing redundant separator may occur. Preserve exact CAL example
  order and repetitions. Do not invent passage IDs or deduplicate text.

The diagnostic trigger was removed after enqueue. The earlier 2-call live
acceptance remains **FAILED**, not retroactively passing. Before any new
one-off live acceptance, first add sibling-fixture RED regression, repair
parser and verify both offline CI configurations; then make and document a
separate bounded decision.
