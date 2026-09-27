# Issue #179 research — current linked Syriac token-analysis redirects

Date: 2026-09-27. Base: `4d19d5a3`.

## Trigger

The release E2E run on 2026-09-25 found that
`cal_token_analysis(coordinate="620570101", word_index=1)` fails closed even though CAL returns a
linked lexical analysis. Issue #170 later showed a second failure for a CPA token; #179 required a
bounded recheck before changing the parser.

Live research was run from a disposable branch so this document remains the first commit on the
implementation branch. The probe made four fixed CAL GETs total across two runs, with 20-second
timeouts, a 256 KiB response cap, no retries, no link traversal, and no neighboring-text crawl.

Research workflow runs:

- `36287513174`: Peshitta word 0, Peshitta word 1, CPA word 0;
- `36287548078`: one additional Peshitta word 2 control;
- `36287854410`: one additional fixed GET of Peshitta word 1 through the production semantic
  line parser to isolate the exact failure mechanism.

Total live research load: five fixed CAL GETs.

## Linked Syriac redirect shape

Current CAL, Peshitta Philemon 1:1:

```text
getlex.php?coord=620570101&word=1
```

returned HTTP 200 (5,007 bytes) with exactly one normal token-analysis marker. The semantic text
between the marker and the result table is currently:

```text
)syr noun sg. emphatic= )syr N --> )syr A
```

The result table contains exactly one `oneentry.php` anchor:

- class: `lexlink`;
- target selector: `lemma=)syr A`;
- selectors: exactly `lemma,cits`;
- rendered linked header: `ˀsyr (ˀăsīr) adj. captured; forbidden`.

The markup is mis-nested in the current upstream HTML. The structural event order is:

```text
<a class="lexlink" ...>
  <span class="lem">...</span>
  <span class="rom">...</span>
  <pos>...</pos>
  <span class="mgP">...
</a>
</span>
```

Thus the link closes while `span.mgP` is still open. The page then renders a full sense outline
outside the result table (three `sense-line` blocks and one `subsense-block` in this response).
That outline is lexicon-entry content, not an additional token-analysis candidate.

The final production-parser probe showed why the current adapter fails. `_parse_lines` returns
the following relevant sequence:

```text
2  Click on a headword to see a complete lexicon entry
3  )syr noun sg. emphatic= )syr N --> )syr A
4  ˀsyr (ˀăsīr) adj. captured; forbidden        [oneentry link]
5  1 captive, bound Com, -OA -BA. ▶ more        [no link]
6  --(a) ... prison : see s.v. byt ˀsyryn ...   [no link]
...
12 ← Return to the Text Browser
```

The legacy alternating-line loop correctly parses lines 3–4 as the first candidate, then advances
to line 5 and treats lines 5–6 as a possible second candidate. Because line 6 contains `s.v.`,
the generic lemma-header heuristic considers it lemma-like; since it has no entry link, the parser
raises `CAL token-analysis candidate lemma header is missing its lemma link`.

Therefore the regression is not failure to see the current `lexlink`. It is failure to stop the
token-analysis candidate region at the end of the current result table. The #179 parser must use
the current table boundary explicitly and must not feed subsequent sense-outline lines back into
the alternating legacy candidate loop.

The redirect is explicit in CAL's rendered analysis label:

```text
)syr N --> )syr A
```

The source/analysed key is `)syr N`; the linked entry target is `)syr A`. The adapter must retain
both rather than replacing the analysis with only the target entry.

## Linkless shapes are separate

The other fixed live examples did **not** return the linked redirect structure.

Peshitta `620570101&word=0` returned one normal result marker followed by:

```text
pwlws PN Personal name
```

with zero `oneentry.php` links.

Peshitta `620570101&word=2` returned:

```text
d_ p = d_ p --> dy p y$w( PN Personal name
```

with zero `oneentry.php` links.

CPA `5500001001a019001&word=0` returned:

```text
lwT PN Personal name
```

with zero `oneentry.php` links.

These are structurally different from the linked `lexlink` redirect and cannot safely be mapped
to `LemmaRef`: CAL supplies no target entry URL/key. They are now tracked as release blocker
#193, **Handle linkless token-analysis summaries (Peshitta and CPA)**. #179 must not make them
`not_found`, synthesize lemma links, or infer candidate boundaries from whitespace.

The Peshitta word-0 observation satisfies the requested live control without a redirect, but it
also proves that “non-redirect Syriac” is not necessarily the legacy linked shape. Existing
fixture-backed Targum/Tel Dan linked analyses remain the compatibility controls for linked
non-redirect parsing.

## Existing adapter contract

Before #179:

- `TokenAnalysisCandidate.analysis_label` preserves CAL's compact rendered analysis label;
- `TokenAnalysisCandidate.lemma` is a linked `LemmaRef`;
- legacy/reduced linked candidates are parsed as alternating semantic lines after the result marker;
- an unlinked lemma-looking header still fails closed;
- the explicit legacy no-data and current no-lemma states map to `not_found`.

The current Syriac redirect page breaks the alternating-line assumption and its malformed nesting
also makes generic line/link association unreliable.

## Representation decision for #179

Keep the existing candidate fields and add one nullable field:

```text
analyzed_lemma_key: string | null
```

It is populated only when CAL explicitly renders a linked redirect of the researched form
`<source key> --> <target key>`.

For the current Syriac example:

```json
{
  "analysis_label": ")syr noun sg. emphatic= )syr N --> )syr A",
  "analyzed_lemma_key": ")syr N",
  "lemma": {"lemma_key": ")syr A", "...": "..."}
}
```

The linked target remains `lemma.lemma_key`. For existing linked non-redirect candidates the new
field is null; CAL-MCP does not retroactively guess an analysed lemma key from older compact labels.

The parser must verify that the rendered redirect target equals the `lemma` selector of the
`oneentry.php` link. A disagreement is parser drift.

## Parser boundary

Add a narrowly scoped parser for the current linked-table shape rather than weakening generic
`_parse_lines` semantics.

The current-shape parser should require:

1. exactly one normal analysis marker;
2. non-empty rendered analysis text between the marker and the result table;
3. exactly one result table candidate for the researched shape;
4. exactly one `a.lexlink` whose route is `oneentry.php`;
5. exactly the existing safe lemma-link selectors/identity required by lexicon helpers;
6. a parseable linked lemma header, including the mis-nested `mgP` close;
7. for redirect notation, one explicit `SOURCE --> TARGET` suffix whose TARGET equals the linked
   lemma key;
8. sense/subsense content after the result table is ignored only as a boundary, never interpreted
   as another token-analysis candidate.

Legacy/reduced candidate parsing remains intact as a compatibility fallback. A current-looking
`lexlink` page that violates the researched structure must fail closed instead of silently falling
back to a looser interpretation.

## TDD boundary

RED must cover:

- the reduced current Peshitta redirect shape and expect both `)syr N` and `)syr A`;
- malformed nesting exactly as current CAL renders it;
- redirect target/link-target disagreement;
- missing `lexlink`;
- repeated `lexlink`;
- malformed/extra link selectors;
- sense-outline text not becoming extra candidates;
- public serialization of `analyzed_lemma_key`;
- existing Targum/Tel Dan-style linked fixtures unchanged with `analyzed_lemma_key=null`.

Linkless summaries remain parser drift under #179 and move to #193.

## Request/data impact

Production request count is unchanged: one explicit token-analysis call is still at most one new
logical CAL request. No entry link or sense-outline link is followed. No CAL corpus or full page is
bundled; the test fixture should retain only the minimal parser-relevant current structure.

## Live acceptance amendment — current Targum also uses the lexlink result table

The first installed-stdio acceptance attempt repaired the Peshitta redirect successfully, then
caught a compatibility regression before merge: current Targum token
`5101801011`, word 0 also uses an `a.lexlink` result table, but **without** redirect notation.
The candidate parser initially treated every `lexlink` as a redirect and rejected it.

A single fixed structural GET then recorded the current Targum shape:

```text
2  Click on a headword to see a complete lexicon entry
3  nbw)h noun sg. emphatic
4  nbwˀh, nbwˀtˀ n.f. prophecy       [oneentry.php?lemma=nbw)h+N&cits=all]
5  prophecy BA-Ez, JLAtg, PTA, CPA, JBA, LJLA. ▶ more
6  --(a) prophetic book JBA.
7  ← Return to the Text Browser
```

The entry anchor has class `lexlink`, exactly the `lemma,cits` selectors, and target
`nbw)h N`. CAL does not render a separate analysed lemma key or `-->` redirect on this token.

Therefore the current table contract is:

- one strict linked `lexlink` candidate bounded by the result table;
- redirect notation is **optional**;
- when an explicit `SOURCE --> TARGET` suffix exists, expose SOURCE as
  `analyzed_lemma_key` and require TARGET to equal the linked lemma key;
- when no redirect is rendered, `analyzed_lemma_key` is null; do not infer it from the free-form
  analysis label.

The sense outline after the table is outside token-analysis candidate parsing in both variants.

Evidence:
- failed installed-stdio acceptance run `36288166906` (Peshitta repaired; Targum regression caught);
- bounded Targum structure run `36288207528` (one CAL GET).
