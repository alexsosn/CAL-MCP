# Issue #177 research — text-concordance rows that CAL marks "no data found"

Date: 2026-09-29 (capture 2026-09-25). Base: `2761efe`.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_text_concordance("41201")` (Palmyrene) fails with `parser_drift` "CAL concordance row lemma key is not canonical". One malformed row costs the user the whole 985-lemma concordance.

## Live-current evidence

The end-to-end capture of `newconcord.php` for text 41201 (99 KB, 985 rows) contains six rows whose gloss is CAL's own "no data found for …" marker:

| Freq. | Decoded KWIC `lemma` | Link label | Gloss |
| --- | --- | --- | --- |
| 1 | `' snqlyTws N'` (leading space; link `lemma=+snqlyTws+N`) | ` snqly+ws N` | `no data found for  snqly+ws N` |
| 1 | `z(yd N` | `z(yd N` | `no data found for z(yd N` |
| 1 | `l p` | `l p` | `no data found for l p` |
| 1 | `qrb ` (no key suffix) | `qrb ` | `no data found for qrb ` |
| 1 | `430 n` | `430 b` | `no data found for 430 b` |
| 1 | `530 n` | `530 b` | `no data found for 530 b` |

```html
1:....<a href="/showKWIC.php?lemma=+snqlyTws+N&charset=S&texts=41201"> snqly+ws N</a>: no data found for  snqly+ws N<br>
```

These are CAL's rows for tokens that are lemmatized to a key with no lexicon entry. CAL says so itself. Some of the keys are not valid CAL lemma keys: one has a leading space encoded as `+`, and one has no suffix. The first one, which reaches the canonical-key check, makes the parser reject the whole page. #149's review had already noted a similar CAL row (`| W.h.`) that passes through.

## Consequences

- A row whose gloss is CAL's explicit `no data found for …` marker is kept, with its frequency, label, gloss and KWIC URL as CAL renders them.
  - Its `lemma_key` is the canonical key when CAL's link carries a valid one.
  - Otherwise it is `null`. This is an additive nullability in the row schema, used only for such rows. CAL-MCP does not repair CAL's key.
- Every other row keeps the strict canonical-key check.
- Request counts are unchanged.
