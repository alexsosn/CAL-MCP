# Issue #193 research — linkless token-analysis summaries

Date: 2026-09-27. Base: `62d89ae2`.

## Trigger

Issue #179 repaired CAL's current linked `a.lexlink` token-analysis table and deliberately left a
different current success shape fail-closed: the normal result marker is present, but CAL renders
analysis text with no `oneentry.php` link from which a `LemmaRef` can be constructed.

The discovery evidence from #179 was rechecked before designing a public representation.

## Bounded live recheck

A disposable research branch made exactly three fixed GETs through the production client. No
pagination, link following, neighboring-token crawl, retries beyond the production client's normal
bounded policy, or corpus download was performed.

Run: `36318521692`.

Current results:

### Peshitta Philemon 1:1, word 0

```text
coord=620570101&word=0
```

After the unique normal result marker CAL renders exactly one semantic line:

```text
pwlws PN Personal name
```

Observed structure:

- HTTP 200;
- no result table;
- zero `oneentry.php` links;
- no semantic links in the summary line.

### Peshitta Philemon 1:1, word 2

```text
coord=620570101&word=2
```

After the unique marker CAL renders two ordered semantic lines:

```text
d_ p = d_ p --> dy p
y$w( PN Personal name
```

Observed structure:

- HTTP 200;
- no result table;
- zero `oneentry.php` links;
- both semantic lines are unlinked.

### Christian Palestinian Aramaic

```text
coord=5500001001a019001&word=0
```

After the unique marker CAL renders exactly one semantic line:

```text
lwT PN Personal name
```

Observed structure:

- HTTP 200;
- no result table;
- zero `oneentry.php` links;
- no semantic links in the summary line.

All three pages use the same outer current CAL shell. The parser-relevant distinction from #179 is
the complete absence of a result table and linked lemma-entry identity.

## Semantic boundary

The live HTML does **not** justify interpreting each rendered line as a full
`TokenAnalysisCandidate`:

- there is no entry URL or canonical linked lemma key;
- the two-line Peshitta response does not mark whether the first line is a candidate, a
  normalization/redirect note for the second line, or another relation;
- `=` and `-->` are rendered text only on this surface. Unlike #179's linked redirect, there is
  no target `lemma` selector against which to verify redirect identity.

Therefore #193 must not decode `=`, `-->`, POS-looking tokens, or gloss-looking text into new
typed lemma fields.

The safest evidence-backed semantic unit is an **ordered rendered summary line**.

## Representation decision

Keep existing linked `candidates` unchanged and add a result/page-level field:

```text
unlinked_summaries: string[]
```

Contract:

- linked CAL analyses remain in `candidates` exactly as before;
- current linkless success pages return `candidates: []` plus one or more ordered
  `unlinked_summaries`;
- summary strings are whitespace-normalized rendered CAL text, with no local morphological,
  lexical, redirect, or candidate-boundary interpretation;
- `status` is `found` when either linked candidates **or** unlinked summaries are present;
- explicit CAL no-data/no-lemma states remain `not_found` with both collections empty.

This is additive and avoids making `TokenAnalysisCandidate.lemma` nullable for a structure that
CAL itself does not identify as a linked lemma candidate.

## Fail-closed boundary

Recognize linkless success only when all of the following hold:

1. exactly one normal token-analysis result marker;
2. no `oneentry.php` / `cal_entry_web.php` lemma-entry links;
3. no current result table after the marker;
4. one or more non-empty semantic lines after the marker and before CAL's return-to-text-browser
   navigation;
5. those summary lines contain no links.

Reject, rather than reinterpret:

- marker-only success pages;
- mixed linked and linkless semantic regions;
- linkless lines containing unexpected links;
- a table without the strict #179 linked-table contract;
- explicit no-data/no-lemma mixed with summary content.

The existing strict #179 current-table parser must retain priority.

## TDD scope

RED must cover at least:

- one-line Peshitta summary;
- two-line Peshitta summary preserving order and punctuation verbatim after whitespace
  normalization;
- one-line CPA summary;
- public serialization and `FOUND` status with zero linked candidates;
- no-data/no-lemma still serialize as `NOT_FOUND` with empty summaries;
- marker-only, unexpected-link, mixed linked/linkless, and table-like drift fail closed;
- existing linked Peshitta/Targum/Tel Dan and legacy multi-candidate fixtures remain unchanged.

## Request/data impact

Production request volume is unchanged: one explicit `cal_token_analysis` call performs at most
one logical CAL request. No summary link is followed, no lexicon entry is synthesized, and no CAL
corpus data is bundled.

## Installed-stdio acceptance

Run `36318994287` installed the candidate wheel and exercised the public MCP server over stdio
with exactly the three researched token-analysis calls:

- Peshitta `620570101`, word 0 → HTTP 200, `status=found`, no linked candidates, one summary;
- Peshitta `620570101`, word 2 → HTTP 200, `status=found`, no linked candidates, the two
  researched summary lines in order;
- CPA `5500001001a019001`, word 0 → HTTP 200, `status=found`, no linked candidates, one
  summary.

No lemma-entry follow-up was performed. The live gate validates the public serialization and the
decision not to invent linked candidates.

## Final post-hardening installed-stdio acceptance

After the empty-state contradiction guards and typing fix, run `36326609176` rebuilt and
installed the candidate wheel and exercised the public MCP server over stdio with exactly the
three researched live calls. All returned HTTP 200 and matched the public contract:

- Peshitta `620570101`, word 0: `status=found`, `candidates=[]`, one exact ordered summary;
- Peshitta `620570101`, word 2: `status=found`, `candidates=[]`, the two researched summaries
  in exact order;
- CPA `5500001001a019001`, word 0: `status=found`, `candidates=[]`, one exact summary.

The run printed no scholarly response text beyond the expected assertion values and performed no
lemma-entry follow-up. The temporary workflow was removed immediately after the successful gate.

## Final review amendment — current explicit no-data page chrome

Exact-head review found that the first no-data hardening pass checked only lines after the
recognized marker. Before tightening the branch further, current CAL was rechecked with one fixed
request:

```text
getlex.php?coord=9999999999999&word=0
```

Bounded structural run: `36326949979`.

The production semantic line parser currently returns exactly:

```text
0  The Comprehensive Aramaic Lexicon                    [no link]
1  ← Back                                               [javascript:history.back()]
2  there is no data for this word — ...                [no link]
```

There is no return-to-text-browser link on this explicit no-data page.

**Implication:** complete-region validation must distinguish the two observed CAL chrome lines from
result semantics. For the current no-data state, the adapter may accept the exact current title/back
prefix (or no prefix in the reduced fixture), but after excluding that recognized chrome there must
be exactly one non-empty semantic line: the unlinked line containing CAL's explicit no-data marker.
Any other pre/post semantic line or any link on the no-data line is parser drift.

This amendment uses one additional fixed CAL GET, no traversal, no retries beyond the shared client
policy, and no corpus data.

## Post-review empty-state acceptance

After the complete no-data-region GREEN, run `36327169454` installed the candidate wheel and
made exactly four public stdio MCP calls against current CAL:

- the three researched linkless Peshitta/CPA examples remained `status=found` with no linked
  candidates and exact ordered `unlinked_summaries`;
- `9999999999999`, word 0 matched the live title/history-back/no-data shape and remained
  `status=not_found` with both result collections empty.

All four upstream requests returned HTTP 200. No lemma link was followed. The temporary workflow
was removed after the successful gate.

