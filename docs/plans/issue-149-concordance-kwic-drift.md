# Issue #149 plan — concordance/KWIC live drift

Date: 2026-09-24. Research is frozen in `docs/research/issue-149-concordance-kwic-drift.md` and was committed before behavior tests.

1. Add reduced current-shape fixtures, each with a provenance comment:
   - `concordance_text_13250_label_current.html`: one display-label row and one key-labelled proper-noun row;
   - `kwic_texts_mlk_br_current.html`: text scope with one empty text, three BR-line hits including a duplicated target, and a matching total;
   - `kwic_dialect_aryk2_a_br_current.html`: single-form dialect page, Hebrew `H` hit;
   - `kwic_dialect_nqh_n_forms_current.html`: requested form with no examples, variant form `nqh N` with one Syriac `U` hit, and a grand total;
   - `kwic_dialect_nqh_n_zero_current.html`: both forms with no examples.
2. RED tests (in a new `tests/test_concordance_kwic_br_current.py`):
   - the concordance label row parses, with `label` preserved and `lemma_key` taken from the link;
   - BR-line text-scope KWIC preserves order, the duplicate target, context (target line minus coordinate), charset and empty scope;
   - single-form dialect KWIC returns `forms == [{)ryk#2 A, 1}]` and `form_lemma_key` on each hit;
   - multi-form dialect KWIC keeps the variant-form hit, charset `U`, total 1 and both forms in order;
   - an all-zero dialect page is a valid empty result with the dialect in `empty_scope_ids`;
   - fail-closed cases: form count ≠ owned hits, a hit after the last summary, hits owned by a `No examples` form, a wrong-dialect summary, a missing or duplicated requested form, a repeated form, a grand total ≠ sum, a non-canonical form key, a hit line whose link text is not the target or does not start the line, a contextless hit line, a hit line with an extra link;
   - `cal_kwic_full_context` accepts `charset="U"` (request construction only; offline);
   - `to_dict` shapes include `label`, `forms` and `form_lemma_key`.
3. A valid RED keeps lint, format and mypy green, with only the new tests failing.
4. GREEN, the smallest change in `src/cal_mcp/concordance.py`:
   - label-tolerant link parsing;
   - BR-line hit mode used only when table mode finds no hit rows;
   - a per-form dialect summary parser with positional hit ownership;
   - `U` added to the KWIC charsets;
   - additive dataclass fields and serializers.
5. Keep all existing table-shape fixtures and regressions green; those parsers remain a strict compatibility fallback.
6. Docs: `docs/tools/concordance.md` (label, target-line context, forms, `U`, the size ceiling), `docs/limitations.md` if needed, `research.md` R-028, `CHANGELOG.md`.
7. Verification: full offline suite, then one bounded live MCP check of the three repaired tools plus one full-context follow-up (about 5 CAL requests), and `live_smoke`.
8. Independent adversarial review of the exact candidate SHA before merge.

Live CAL load for implementation: zero until step 7.
