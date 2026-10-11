# Research — CAL dialect KWIC unrendered hit notices (#266)

Date: 2026-10-10. No new CAL requests. Based on the JBA mlk N dialect 71 evidence in issue #266 and the actual current source, reduced KWIC fixtures and data models in src/cal_mcp/concordance.py.

Current page show1dialectKWIC.php?lemma=mlk&pos=N&texts=71 is approximately 228 KiB and advertises 271 examples for form mlk) N. Between normal KWIC hit paragraphs it contains the full text line:

    error: line not found for 71600222x004133

This is a real CAL diagnostic-only unrendered item with an opaque x-bearing coordinate, NOT a rendered hit. No target URL/book/subtext may be invented and the diagnostic must not be silently discarded. The current broad _DIALECT_SUMMARY_HINT_RE incorrectly matches "found for" inside this notice, falsely raising parser drift. Simply skipping the line is also wrong: _assign_dialect_forms currently requires per-form total == count of rendered hit lines. CAL's advertised total can contain both rendered and unrendered items.

Model change: add an ordered, typed unrendered_hits result separate from rendered hits. Preserve the complete literal CAL diagnostic, opaque coordinate and owning form as determined by validated source-line intervals. Parse only an exact full-line marker with a bounded ASCII alphanumeric coordinate; do not broadly ignore unknown summary text. Reconcile each returned per-form total to rendered plus explicitly unrendered entries and preserve the upstream total as advertised. Zero placeholder target URLs, no retries/fetches. Existing rendered KWIC coordinate/link validation remains unchanged.

Possible text-scoped equivalents are not established by the current issue's live evidence. Do not silently extend text-scoped handling: fail closed until source-backed research. No new CAL load while issue #262 demonstrates HTTP 429.
