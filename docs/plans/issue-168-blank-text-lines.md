# Issue #168 plan — preserve CAL empty lexical word slots

Date: 2026-09-26. Research was committed before behavior changes and amended after live verification
showed that the initial single-blank-line hypothesis was incomplete.

1. Preserve the original reduced all-empty row fixture for coordinate `60424100508`.
2. Add a clearly marked structural mixed-row fixture using live-observed coordinate `60424100523`:
   a rendered word-0 link plus the observed empty word-1 slot. No uncaptured scholarly token text is
   represented as CAL data.
3. RED tests through `TextService.page`:
   - all-empty row → coordinate preserved, `text=""`, `tokens=[]`,
     `empty_word_indexes=[0]`;
   - mixed row → rendered token remains in `tokens`, empty slot is kept in
     `empty_word_indexes=[1]`, and line text contains only rendered text;
   - ordinary current rows → `empty_word_indexes=[]`;
   - empty slot with altered route/selectors, non-positive/non-decimal coordinate or nonnumeric
     word index fails closed;
   - empty and rendered links naming different coordinates fail closed;
   - duplicate empty indexes and empty/rendered index collisions fail closed.
4. Demonstrate the new RED against the current partial implementation before revising production
   code.
5. GREEN only in the current table-row reader. Keep the generic `_token_from_link` contract
   unchanged.
6. Add additive `TextLine.empty_word_indexes` serialization and user documentation; no new tool
   or request is introduced.
7. Run both deterministic CI matrices.
8. Delete the temporary live-research workflow.
9. Verify installed `cal-mcp` over stdio against live `cal_text_page("60424")`: the operation
   succeeds and exposes the known all-empty slot plus mixed empty slots.
10. Perform a new logically independent adversarial review of the exact final SHA, including the
    superseded acceptance criterion and fail-closed guards. Merge only after approval and green CI.
