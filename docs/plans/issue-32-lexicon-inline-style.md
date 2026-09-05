# Issue #32 plan — exclude non-content HTML from lexicon semantic extraction

## Goal

Restore correct `entry.lemma` parsing for current `cal_entry_web.php` pages that inline stylesheet/script content, without changing the public lexicon contract or downstream sense/citation parsing.

## Frozen implementation boundary

Production change is limited to `_SemanticHTMLParser` in `src/cal_mcp/lexicon.py`:

- maintain ignored-subtree depth for `style` and `script`;
- do not collect data, block boundaries, or links while inside ignored subtrees;
- resume normal semantic extraction only after the matching ignored subtree closes;
- leave all lemma, sense, citation, derivative, normalization, request, cache, provenance, and MCP code unchanged unless a failing regression proves an additional minimal change is required.

No switch to `<meta name="cal-lemma">` is included.

## TDD gate

Before production modification, add offline failing coverage that proves current code is wrong:

1. a reduced current-shape full-entry fixture with inline style + script sentinels and eight senses for `b s`;
2. parser assertions for `b / sym. / second letter of alphabet` and eight senses;
3. recursive/public-model contamination assertion covering lemma, senses, citations, derivatives, notes, grammar, and form-usage strings;
4. browse/full-entry agreement assertion using the same canonical lemma key;
5. retain existing pre-drift entry fixtures as backward-compatibility coverage.

The valid RED must have install, Ruff lint/format, and strict mypy green while pytest fails specifically because the inline stylesheet/script is being harvested as semantic text.

## Implementation gate

Implement the smallest ignored-subtree mechanism in `_SemanticHTMLParser`. Do not add CSS-token heuristics or post-parse string filters.

## Test gate

Require the complete deterministic repository gate:

- install;
- Ruff lint;
- Ruff format check;
- strict mypy;
- full pytest suite.

The new regression must go green while existing lexicon and non-lexicon tests remain unchanged.

## Documentation gate

Append a dated upstream-drift note to `research.md` describing CAL's 2026-09-05 inline stylesheet change and the adapter rule that non-rendered `style`/`script` content is excluded from semantic extraction. No public tool documentation change is expected because the public contract is unchanged.

## Independent review gate

Freeze an exact green SHA and review skeptically against issue #32 and this plan. Review must explicitly challenge:

- whether ignored-subtree handling survives repeated/nested tags;
- whether links or rendered text adjacent to ignored elements can be lost or merged incorrectly;
- whether the fix is overly broad for browse pages;
- whether tests would fail if style suppression were removed;
- whether sense-count and browse/full-entry agreement guarantees remain covered;
- whether any CSS/script sentinel can still leak into returned public fields.

Any blocker enters a fresh regression RED → minimal fix → full GREEN → exact-SHA re-review sub-loop.

## Merge gate

Only after a clean independent review: mark the PR ready, guarded-squash merge with expected head SHA, and verify issue #32 closes before starting #31.
