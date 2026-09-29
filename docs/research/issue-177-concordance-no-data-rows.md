# Issue #177 research — text-concordance rows that CAL marks "no data found"

Date: 2026-09-29 (capture 2026-09-25). Base: `2761efe`.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_text_concordance("41201")` (Palmyrene) fails with `parser_drift` "CAL concordance row lemma key is not canonical". One malformed row costs the user the whole 986-lemma concordance.

## Live-current evidence

The end-to-end capture of `newconcord.php` for text 41201 (99 KB, 986 rows) contains six rows whose gloss is CAL's own "no data found for …" marker:

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

## Answers to the issue's research questions

- **How `+` is encoded:** CAL writes a literal `+` in the query string (`lemma=+snqlyTws+N`). Under standard form decoding, which is also what CAL's own PHP applies, `+` is a space, so the key CAL links is `' snqlyTws N'`. The `+` inside the *label* (`snqly+ws`) is CAL's display for the key's `T` (ṭ). It is not a loanword marker in the key. CAL-MCP does not guess a "true" key; CAL itself says it has no data for this lemma.
- **Round-trip:** a row whose key is not valid has `lemma_key: null`, so there is nothing to pass to `cal_lexicon_lookup` or `cal_kwic_texts`. The row's `kwic_url` is still CAL's own link.

## Second finding (2026-09-29): capital letters in real keys

Parsing the whole capture after the no-data fix found four ordinary proper-noun rows whose keys use ASCII capitals that are not documented `cal_code` letters: `bwlbrK PN`, `bryK PN`, `prnK PN` and `$lMn) PN`, each with frequency 1 and gloss `proper noun`. No other captured key in the scratch captures has characters outside `cal_code` apart from homograph digits.

Bounded live checks, four requests:

| Request | Result |
| --- | --- |
| `GET showKWIC.php?lemma=bwlbrK+PN&charset=S&texts=41201` (the row's own `kwic_url`) | `Looking for bwlbrK PN in file 41201`, 1 example (`412012251002`, `b[wlbr]`) |
| `GET showKWIC.php?lemma=%24lMn%29+PN&charset=S&texts=41201` | 1 example (`412015351002`, `šlm|nʾ`) |
| `POST showdialectKWIC.php` `lemma=bwlbrK`, `pos=PN`, `texts=41201` (the `cal_kwic_texts` request) | `Looking for bwlbr PN in dialect 41201`, `total examples: 0` |
| same with `lemma=bwlbr` | same heading, 0 examples |

So these are real CAL keys with real hits. CAL's KWIC-by-text form drops the capital, echoes a different key, and finds nothing. Consequences:

- Concordance rows keep such keys verbatim. Only the observed capitals `K` and `M` are exempted from the alphabet check, and only for keys CAL itself returns in concordance rows; the rest of the key is still validated, so all-capital or other-capital keys still fail closed.
- The KWIC tools reject such keys as **input** with `invalid_input` and a message pointing to the row's `kwic_url`. Sending the request would get a mismatched heading (`parser_drift`) or, if relaxed, a false "0 examples".
