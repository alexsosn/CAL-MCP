# Issue #261 — CAL's unclosed dialect tag inside Peshitta token sense outlines

Date: 2026-10-10. Grounded in the 2026-10-10 installed-wheel Peshitta John 1:1–4 E2E evidence preserved in issue #261 and the actual `src/cal_mcp/token_analysis.py` segment parser. **No new CAL requests** in this research gate; CAL reported HTTP 429 for 6 of the 37 prior token calls (issue #262), so fresh page probes are deferred until process-wide pacing is accepted.

## Reproduction and source

The previously observed `getlex.php?coord=620430101&word=1` returns HTTP 200 with a normal linked `)yt V` result table followed by its sense outline. CAL emits the syntactically unclosed tag:

```html
<span class="dial-tag"><dial dnumber="00" title="Common Aramaic">Com</dial>,
<sup><dial title="except for OA">-OA</sup></span>
```

Only the inner dialect **inside `sup`** is unclosed; `</sup>` is intended to terminate that inline exclusion. The existing parser's `_CurrentSegment.post_table_depth` is a blind integer counting opening/closing elements after the result table. The unmatched `<dial>` leaves nonzero depth, causing a later legitimate segment-separating `<hr>` to be classified as `post_table_loose` and reject the entire source as `parser_drift`. The issue's offline mutation (adding `</dial>` before `</sup>`) confirms the diagnosis. At least 15 of the previously analysed 31 reachable token pages exhibited the same error; other upstream shapes need separate evidence.

## Scope and edge boundary

Track only *non-void, non-optional* post-table element names in addition to depth. When `</sup>` closes a direct `sup > dial` suffix of that stack, implicitly close precisely that `dial` before closing `sup`; this is a narrow CAL-source compatibility rule. A missing closing tag other than that exact `dial` shape, a second result table, stray text outside the outline or `<hr>` inside an open outline must remain parser drift. Do not strip the outline's content into a fabricated lemma or disable post-table boundary checking wholesale.

The CAL lexical entry and citation-context readers do not share this `_CurrentLinkedRedirectParser` after-table depth counter. They need no changes absent a separately reproduced failure (the issue's request to check other sense consumers is not permission to broaden them speculatively).

A valid 37-token real-MCP acceptance requires **both** #261 and #262; a one-shot #262 run on the pre-#261 source might stop on an already documented parser drift, and should not be read as disproving pacing or as a reason to probe again without a separate reviewed decision.
