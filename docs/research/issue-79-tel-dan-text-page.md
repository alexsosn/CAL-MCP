# Issue #79 research — Tel Dan `cal_text_page` retrieval regression

Date: 2026-09-08
Baseline: `main` at `d704ee5c2b542e22c22a3929771fa466dea0a0f6`.

Research in progress. This file records the ticket and baseline before the bounded live probe; findings and implementation implications will be completed before the plan and before tests/production changes.

Issue #79 reports that `cal_text_search("Tel Dan")` returns file `13250` (`TDanStel (Tel Dan Stele)`) with no subtext, while `cal_text_page(file_id="13250", page=1)` currently surfaces only a generic execution error. Existing offline coverage predates the report and models Tel Dan as a valid unpaginated text page.

No implementation assumption is frozen until the current CAL response shape is rechecked with a tiny fixed probe.