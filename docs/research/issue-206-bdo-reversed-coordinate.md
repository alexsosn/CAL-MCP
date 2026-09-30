# Issue #206 research — KWIC coordinates written reversed inside `<BDO dir="rtl">`

Date: 2026-09-29. Base: `c9892c7`.

## Trigger

While smoke-testing #203, `cal_kwic_texts("gml N", ["71002"], script="hebrew")` (Babylonian Talmud, Shabbat) failed with `parser_drift` "CAL KWIC target link text differs from its coordinate".

## Live-current evidence

Two bounded `POST showdialectKWIC.php` requests through the production client on 2026-09-29, both with `charset=H`:

| Request | Hits | Target link |
| --- | --- | --- |
| `gml N`, `texts=71002` (BT Shabbat) | 2 | `…target=7100201077225"><span class="mono"><BDO dir="rtl">5227701020017</BDO></span></a>` |
| `mlk N`, `texts=13250` (Tel Dan) | 6 | `…target=1325003"><span class="mono"><BDO dir="rtl">3005231</BDO></span></a>` |

Every target coordinate on these Hebrew-script pages is written in reverse digit order inside `<BDO dir="rtl">`, so that a right-to-left display shows it in the right order. The context lines' coordinates follow the same convention (`4227701020017` = `7100201077224`). This affects **every** `script="hebrew"` KWIC request, not only BT: the Tel Dan page fails the same way. The Roman-script pages checked in earlier issues render the coordinate plainly, with no `BDO`.

## Consequences

- A target link's text is accepted when it is exactly the target coordinate, or when it is exactly the coordinate reversed **and** the whole link text sits inside `<BDO dir="rtl">`. A reversed coordinate outside such an element, a mixture of the two, or any other text fails closed.
- The returned `target_coordinate` is always the link's `target` value, which is never re-derived from rendered text.
- Production requests are unchanged.
