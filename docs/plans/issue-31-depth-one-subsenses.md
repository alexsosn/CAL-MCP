# Issue #31 plan — support depth-1 parenthetical sense siblings

## Goal

Allow current CAL entries whose sense outline begins `(1) (2) (3) ...` to parse completely while retaining the existing fail-closed guard for non-consecutive numbering.

## Frozen production change

Change only `_subsense_path()` unless a failing regression proves more is required. Its existing deepest-to-shallowest sibling search must include index `0`.

Expected algorithmic behavior:

- first parenthetical label: unchanged;
- `value == 1`: unchanged deeper-child behavior;
- for `value > 1`, search all path positions from deepest through index 0 for `value - 1`;
- if no predecessor exists, continue to raise `LexiconParseError`.

No public MCP/result changes and no permissive fallback.

## RED gate

Add tests before production change for:

1. depth-1 siblings `(1,) -> 2 -> (2,)`;
2. complete depth-1 run `(1) (2) (3) (4)`;
3. unsafe jump `(1,) -> 4` still raises;
4. deeper sibling `(2,1) -> 2 == (2,2)` remains unchanged;
5. zero/negative value remains rejected;
6. reduced `)lh N` fixture returns four complete sibling senses.

Accept RED only when install, Ruff lint/format, and strict mypy pass and pytest fails on the new depth-1 behavior.

## Implementation/test gate

Apply the one-boundary algorithm fix and run the complete deterministic repository suite. Existing nested-sense and lexicon drift regressions must remain green.

## Documentation gate

Add a concise dated root research record that current CAL can begin an entry with parenthetical sense numbering at depth 1. If `docs/tools/lexicon.md` describes sense paths, mention that CAL's rendered numbering may omit an enclosing plain-numbered level; adapter paths preserve the observed hierarchy rather than inventing one.

## Independent review gate

Freeze an exact green SHA and review the full PR skeptically. Challenge at least:

- off-by-one behavior at index 0;
- jump/non-monotonic rejection;
- whether searching index 0 could incorrectly collapse a deeper path;
- repeated `(1)` child behavior;
- deeper sibling behavior from existing fixtures;
- whether the parser fixture proves four siblings rather than merely no exception.

Every blocker requires a new regression RED, minimal fix, full GREEN, and exact-SHA re-review.

## Merge gate

Only after clean independent review: ready PR, guarded squash merge using the reviewed head SHA, verify #31 closes, then re-triage open bugs before returning to paused feature PR #30.
