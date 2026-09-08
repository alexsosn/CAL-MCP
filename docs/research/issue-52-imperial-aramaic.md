# Issue #52 research — Imperial Aramaic Unicode → CAL code

Date: 2026-09-07

## Scope

This gate covers only the dedicated Unicode **Imperial Aramaic** block. It does not add Palmyrene, Nabataean, Hatran, Samaritan, or Mandaic mappings.

## CAL corpus relevance

CAL's current dialect taxonomy has a first-class `2 Imperial Aramaic` family with General, Mesopotamian, Egyptian, Persian-administration, Samarian, Iranian/Afghan/Pakistani, and western subgroups:

- https://cal.huc.edu/Cal_dialect_codes.html
- https://cal.huc.edu/newshow_browsedialects.php?R1=2

The current Imperial Aramaic catalogue includes TAD corpora such as TAD C1.1 (Ahiqar), file `23600`, among many other Official Aramaic texts. This establishes a real CAL corpus family for the dedicated script.

## Unicode character identity

Unicode encodes Imperial Aramaic at U+10840–U+1085F. The standard describes the script as an alphabetic script of 22 consonant letters with no vowel marks. The letter repertoire is:

- U+10840 IMPERIAL ARAMAIC LETTER ALEPH
- U+10841 BETH
- U+10842 GIMEL
- U+10843 DALETH
- U+10844 HE
- U+10845 WAW
- U+10846 ZAYIN
- U+10847 HETH
- U+10848 TETH
- U+10849 YODH
- U+1084A KAPH
- U+1084B LAMEDH
- U+1084C MEM
- U+1084D NUN
- U+1084E SAMEKH
- U+1084F AYIN
- U+10850 PE
- U+10851 SADHE
- U+10852 QOPH
- U+10853 RESH
- U+10854 SHIN
- U+10855 TAW

Authoritative Unicode references:

- https://www.unicode.org/charts/PDF/U10840.pdf
- https://www.unicode.org/versions/Unicode16.0.0/UnicodeStandard-16.0.pdf §10.4

The remainder of the block contains the section sign and numeric characters; those are not consonantal lexical input and are excluded from this conversion slice.

## Exact CAL correspondence

CAL's current Roman code table (`https://cal.huc.edu/prova.html`) assigns its core consonantal codes by the same named Semitic consonants:

`ALEPH )`, `BETH b`, `GIMEL g`, `DALETH d`, `HE h`, `WAW w`, `ZAYIN z`, `HETH x`, `TETH T`, `YODH y`, `KAPH k`, `LAMEDH l`, `MEM m`, `NUN n`, `SAMEKH s`, `AYIN (`, `PE p`, `SADHE c`, `QOPH q`, `RESH r`, `SHIN $`, `TAW t`.

The mapping below is therefore based on Unicode **character identity/name matched to CAL's documented consonant identity**, not on code-point/alphabet order:

| Unicode | name | CAL code |
| --- | --- | --- |
| `𐡀` U+10840 | ALEPH | `)` |
| `𐡁` U+10841 | BETH | `b` |
| `𐡂` U+10842 | GIMEL | `g` |
| `𐡃` U+10843 | DALETH | `d` |
| `𐡄` U+10844 | HE | `h` |
| `𐡅` U+10845 | WAW | `w` |
| `𐡆` U+10846 | ZAYIN | `z` |
| `𐡇` U+10847 | HETH | `x` |
| `𐡈` U+10848 | TETH | `T` |
| `𐡉` U+10849 | YODH | `y` |
| `𐡊` U+1084A | KAPH | `k` |
| `𐡋` U+1084B | LAMEDH | `l` |
| `𐡌` U+1084C | MEM | `m` |
| `𐡍` U+1084D | NUN | `n` |
| `𐡎` U+1084E | SAMEKH | `s` |
| `𐡏` U+1084F | AYIN | `(` |
| `𐡐` U+10850 | PE | `p` |
| `𐡑` U+10851 | SADHE | `c` |
| `𐡒` U+10852 | QOPH | `q` |
| `𐡓` U+10853 | RESH | `r` |
| `𐡔` U+10854 | SHIN | `$` |
| `𐡕` U+10855 | TAW | `t` |

There is no Imperial-Aramaic-specific sin grapheme in this Unicode repertoire, so this slice does not invent `&` alternatives.

## Attested CAL fixture

CAL's live lexicon entry for `mn` includes the Imperial/Official Aramaic citation:

- source: TAD C1.1 (Ahiqar)
- stable CAL corpus file: `23600`
- citation locator: `.139`
- CAL/transliteration sequence in the citation: `mn`
- retrieval date: 2026-09-07
- source URL: https://cal.huc.edu/oneentry.php?cits=all&lemma=mn+R

For the dedicated-script regression fixture, the same consonantal sequence is encoded by character identity as:

- Unicode input: `𐡌𐡍` = U+1084C IMPERIAL ARAMAIC LETTER MEM + U+1084D IMPERIAL ARAMAIC LETTER NUN
- expected CAL candidate set: `("mn",)`

This is citation-sized evidence only; no CAL page or corpus is copied into the repository.

## Failure / ambiguity boundary

Supported in this slice:

- the 22 Unicode Imperial Aramaic consonant letters;
- ordinary ASCII spaces between words, following the existing converter word contract.

Explicitly rejected:

- U+10857 IMPERIAL ARAMAIC SECTION SIGN;
- U+10858–U+1085F numeric characters;
- any other punctuation/editorial marks;
- mixed Imperial Aramaic plus another script unless a future mixed-script contract is researched.

No finite grapheme ambiguity was found in the Unicode Imperial Aramaic consonant repertoire. Therefore every supported Imperial Aramaic word has exactly one CAL-code candidate.

## Implementation implication

Add an explicit `imperial_aramaic` input representation and `imperial_aramaic_to_cal_code` conversion strategy. Detection must be range-aware but validation must accept only the 22 researched consonant letters (plus existing word separators), not every code point in U+10840–U+1085F.

Implementation remains table-driven. Tests must demonstrate the full 22-letter edge/table mapping, the attested `𐡌𐡍 → mn` fixture, explicit rejection of section sign/numbers, and unchanged behavior for existing representations.
