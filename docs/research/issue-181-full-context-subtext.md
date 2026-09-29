# Issue #181 research — full-context file-info coordinate for subdivided texts

Date: 2026-09-29. Base: `fc66170`.

## Trigger

The independent review of #166 (2026-09-25) found that `cal_kwic_full_context` fails for hits in subdivided texts. For `get_a_kwicchapter.php?file=56000&sub=112&cset=R&target=56000112010`, CAL renders `get_file_info.php?coord=56000112` with the label `56000: SamTgJ Gen chapter 12`. The parser raises "CAL full-context file-information label differs from its identifier" because it requires the label to start with the coordinate and the coordinate to equal the file id.

## Live-current evidence

Three bounded GETs through the production client on 2026-09-29. Each is the exact request `cal_kwic_full_context` sends for a KWIC hit already captured in the end-to-end runs.

| Request (`file`, `sub`, `cset`, `target`) | File-info link |
| --- | --- |
| `56000`, `112`, `R`, `56000112010` (Samaritan Targum) | `coord=56000112`, `56000: SamTgJ Gen chapter 12` |
| `41201`, `049`, `R`, `412010491005` (Palmyrene) | `coord=41201049`, `41201: C3949 (PAT 0295)` |
| `71002`, `01051`, `H`, `7100201051217` (BT Shabbat, Hebrew script) | `coord=71002`, `71002: BT Sab` |

## Findings

- As on text pages (#166, R-039), the coordinate is either the file id followed by the exact submitted `sub`, or the bare file id. Both forms occur on current CAL for different texts.
- The label prefix is always the file id, not the coordinate.

## Consequences

- Full-context identity accepts exactly one file-information link whose coordinate is the requested file id or the file id plus the submitted sub, and whose label starts with `<file id>:`.
- Anything else fails closed: a coordinate naming another file or subtext, a label naming another file, or repeated links.
- Production requests are unchanged.
