# Issue #42 research — current single-text concordance drift

**Rechecked:** 2026-09-06

This note records the bounded current-source evidence for issue #42 before any production parser change. Normal CI remains offline.

## Release failure being reproduced

The v0.1 release probe reported that the existing public operation

```text
cal_text_concordance(text_id="13250", script="semitic")
```

still receives HTTP 200 from the expected private CAL endpoint but raises `ConcordanceParseError: CAL text concordance contains no recognizable lemma rows`.

The existing reduced fixture in `tests/fixtures/cal/concordance_text_13250.html` represents every lemma as a three-cell table row: frequency cell, `showKWIC.php` link cell, and gloss cell. `parse_text_concordance_page()` currently requires that table-row shape after validating the page marker.

## One-request current CAL recheck

A temporary branch-only workflow at commit `57d5eb9db286e09122e1590884c384c6ab4e1de5` made exactly one GET to:

```text
https://cal.huc.edu/newconcord.php?text=13250&cset=S
```

GitHub Actions run `34041622200` completed successfully. The request used a 20-second timeout, no retry loop, and a 256 KiB response cap. The response was:

- HTTP 200;
- `text/html; charset=UTF-8`;
- 7,071 bytes;
- one `Frequencies of lemmas in text 13250` marker;
- 41 `showKWIC.php` links, each still carrying `lemma`, `charset=S`, and `texts=13250`.

The preliminary workflow commit was rejected by GitHub's YAML parser before any job existed, so it issued no CAL request. The successful probe workflow was deleted immediately afterward; its deletion commit cannot satisfy the probe job condition and therefore cannot issue another request.

## Current semantic shape

CAL has not changed the request contract or the meaning of the result. It changed the lemma-row markup.

Representative current structure is an inline stream inside a `span` with rows separated by `<br>`:

```html
<span class="mono">
4:.......<a href="/showKWIC.php?lemma=%29b+N&amp;charset=S&amp;texts=13250">)b N</a>: father<br>
1:.......<a href="/showKWIC.php?lemma=%29x%29b+PN&amp;charset=S&amp;texts=13250">)x)b PN</a>: proper noun<br>
</span>
```

The stable semantic components remain the same:

1. integer frequency before the link;
2. one CAL `showKWIC.php` lemma link;
3. linked lemma text equal to the decoded `lemma` query value;
4. linked `texts` value equal to the requested text ID;
5. linked `charset` value equal to the requested rendering;
6. non-empty gloss after the linked lemma.

The existing shared semantic HTML extractor already flushes on `<br>` and preserves links, so current rows can be represented as one semantic line apiece without adding another HTML stack.

## Parser consequence

The correction should accept the current inline semantic-row shape while keeping the existing table parser as a strict compatibility fallback. Current inline mode should:

- identify numeric frequency-prefixed semantic lines;
- require exactly one `showKWIC.php` link on each candidate row;
- validate CAL origin/path and the single `lemma`, `texts`, and `charset` values exactly as the table path does;
- require linked text to equal the decoded lemma key;
- require a non-empty gloss after the link;
- preserve upstream order and frequencies;
- fail closed if a candidate row is partial, has multiple relevant links, contradicts the request, or if no rows are recognizable.

No public model/schema, request parameter, pagination behavior, provenance field, or network call count needs to change. One public `cal_text_concordance` call remains one CAL GET.

## Fixture policy

The regression fixture should contain only the heading marker and a few representative inline `<br>` rows from text `13250`, sufficient to reproduce the current parser failure. It must not archive the 7 KB page or all 41 CAL rows.

## Source and load

- CAL: `https://cal.huc.edu/newconcord.php?text=13250&cset=S`
- bounded live evidence: GitHub Actions run `34041622200`, 2026-09-06
- successful CAL requests for this recheck: **1**
- enumeration/pagination/follow-up requests: **0**
