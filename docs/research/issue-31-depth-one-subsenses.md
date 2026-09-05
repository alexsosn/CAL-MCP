# Issue #31 research — depth-1 parenthetical sense numbering

Date: 2026-09-05

## Current evidence

Issue #31 records a bounded live check of `oneentry.php?lemma=)lh N` on 2026-09-05. The current CAL entry starts its sense outline with the token sequence `(1) (2) (3) (4)` and no enclosing plain-numbered top-level sense. The same failure class was observed for `)r( N`.

The adapter treats plain numeric labels with `_NUMBER_RE` and parenthetical labels with `_SUBNUMBER_RE`. Parenthetical labels are placed by `_subsense_path(previous, value)`.

Current implementation on `main`:

```python
for index in range(len(previous) - 1, 0, -1):
    if previous[index] == value - 1:
        return (*previous[:index], value)
```

The stop value `0` is exclusive. Consequently index 0 is never considered. After `(1)` establishes path `(1,)`, `(2)` reaches an empty loop and raises `LexiconParseError` even though CAL is expressing a normal sibling at depth 1.

Direct semantic table:

- no previous path + `(1)` → `(1,)`;
- `(1,)` + `(2)` should → `(2,)`;
- `(1,)` + `(4)` must still raise as an unsafe jump;
- `(2, 1)` + `(2)` already → `(2, 2)` and must remain unchanged;
- a new `(1)` after an existing path still opens one deeper level by existing policy.

## Scope

The defect is entirely in sibling placement. The smallest correction is to let the existing deepest-to-shallowest search include index 0. No fallback, renumbering, partial-entry behavior, or public result-shape change is needed.

Trailing plain-number tokens observed on the live page may represent citation counts; issue #31 explicitly leaves that separate and this fix does not broaden label recognition.

## Offline evidence required

Before production modification, tests must pin:

- `_subsense_path((1,), 2) == (2,)`;
- a depth-1 `(1) (2) (3) (4)` run produces four sibling paths;
- `(1,) -> 4` still raises `LexiconParseError`;
- deeper sibling placement remains unchanged;
- zero/negative labels remain rejected;
- a reduced `)lh N` full-entry shape parses all four senses without changing the public entry model.

Normal CI remains offline; the live evidence is already recorded in issue #31 and no further CAL request is required for this local algorithm defect.
