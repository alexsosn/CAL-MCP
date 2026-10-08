# Issue #180 plan — name the unsupported Hebrew mark in conversion errors

This change is local only, with no CAL request. The behaviour stays the same: pointed Hebrew is
still rejected by the converter. Only the error text changes.

## Current defect

In `_convert_hebrew_word`, every combining mark after `ש` is collected. Any list other than
exactly one shin or sin dot is reported as a shin/sin-dot problem. NFC orders qamats (ccc 18)
before the shin dot (ccc 24), so `שָׁלוֹם` reports
"supports only one explicit shin or sin dot", although the real obstacle is the vowel. The other
mark errors do not name the offending character either.

## Change

- The first combining mark that is not a shin or sin dot raises a vowel/accent/mark error. It
  names the mark's code point and Unicode name (`U+05B8 HEBREW POINT QAMATS`) and suggests the
  word with all other marks removed, keeping shin/sin dots (`שׁלום`). The suggestion is shown
  only; the converter never applies it.
- A shin with only dots, but more than one (`שׁׁ`, or a shin dot plus a sin dot), keeps the
  existing shin/sin message.
- A mark with no letter before it, and an unmapped character, also name the code point.
- The message does not mention `cal_lexicon_lookup`, because lookup re-raises this same error
  when its native fallback does not apply. The docs explain lookup's pointed-input route instead.

## Tests (RED first)

- `שָׁלוֹם` → names U+05B8 HEBREW POINT QAMATS and suggests `שׁלום`, not the shin/sin message.
- `בָּרָא` → names U+05B8 HEBREW POINT QAMATS, the first mark in canonical order, and suggests `ברא`.
- `שּׁ` (dagesh with shin dot) → names the dagesh.
- `שׁׁ` and shin dot plus sin dot → still the shin/sin message.
- `מלך־רב` → the unmapped-character message names U+05BE HEBREW PUNCTUATION MAQAF.
- Existing shin/sin ambiguity tests are unchanged.
