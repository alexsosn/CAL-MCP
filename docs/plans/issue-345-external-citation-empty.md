# Issue #345 — research → plan → TDD → test → adversarial review

1. Freeze exact source SHA and live 1CorH empty evidence, confirm parser's explicit no-citation state is legitimate and source membership does not imply nonempty citations; plan one bounded alternative `EbPar` case from current selector.
2. **RED before implementation:** unit tests of candidate selection: accept exact `EbPar` only from a source list with canonical CAL URL and correct dialect `6`; reject missing, malformed, duplicate-query, wrong-host, aliased, fragment, and absent selectors; refuse zero-success as positive. Test sanitary report shape, no quoted lexical text, no early second call. Confirm expected RED with both CI configurations; original suite remains green.
3. Implement small opt-in installed-wheel diagnostic using existing CalHttpClient and ExternalCitationService, fixed two-call cap, nonpublishing workflow only once, 60-second gap between calls and no concurrent live jobs. Do not weaken parser or run a broad catalogue scan.
4. Preserve full source `citations` only inside process memory and print at most exact source code, status (positive/empty), count and sanitized exception category. No raw CAL page, citation, lemma, translation, bibliography data.
5. If positive, add a positive-case CAL-MCP follow-up smoke using a reviewed same-origin typed selector derived from fresh source list. Run offline CI and one installed-wheel MCP smoke with attempt ceiling. If empty, record actual legitimate result and stop; do not fabricate pass.
6. Independent adverse review on the real code and measured data, then merge only with exact-head CI green. Keep v0.2.0 blocked by #340 until all-37 exact-candidate E2E gate is passed. Remove one-off workflows before merging.


## Completion evidence and scope correction

- Initial original issue assumption (`1CorH` current no-citations) was unsupported. Both alleged empty responses were actually incorrectly validated under the frozen `external_citations` dialects case ID. Current `1CorH` citation count is unknown.
- RED [CI #43760033363](https://github.com/alexsosn/CAL-MCP/actions/runs/43760033363) caught the collision; further checks found `kwic_dialects` and `targum_concordance` also shared case IDs across smoke matrices. All three *internal* dependent IDs are now unique. The external positive requirement was **not weakened**.
- Two source-only paced probes independently returned 26 CAL-derived `EbPar` citations; no change was required in `ExternalCitationService`.
- Rebuilt-wheel [stdio MCP #43760566728](https://github.com/alexsosn/CAL-MCP/actions/runs/43760566728) passed the full 3-call dependent external path with exactly three actual CAL starts and a required nonempty `citations` array. Disposable workflows and source diagnostic are removed before merge.
- Continue independent exact-head adversarial review + pinned/latest CI gates, merge PR #346, then the all-37 exact-candidate validation in #340. No release tag or PyPI publishing action in this ticket.
