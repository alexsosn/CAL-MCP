# Issue #52 research — Hatran Unicode → CAL code

Date: 2026-09-07

## Scope

This gate covers only the dedicated Unicode **Hatran** block. Imperial Aramaic, Palmyrene, and Nabataean are already implemented under separate gates; Samaritan, Mandaic, and CPA/Syriac evidence remain separate slices.

## CAL corpus evidence

CAL exposes Hatran lexical/corpus citations. The current CAL entry for `klb` is labelled `Hatran, Syr` and contains the Hatran citation `H 71:.1 nrgwl klbˀ`.

- https://cal.huc.edu/cal_entry_web.php?lemma=klb%233+N
- retrieval date: 2026-09-07

This supplies the clean citation-sized consonantal fixture `klb` without requiring any corpus redistribution.

## Unicode repertoire

The current Unicode names list encodes Hatran letters at U+108E0–U+108F5 with one crucial representational merger:

- U+108E0 ALEPH
- U+108E1 BETH
- U+108E2 GIMEL
- U+108E3 **DALETH-RESH**
- U+108E4 HE
- U+108E5 WAW
- U+108E6 ZAYN
- U+108E7 HETH
- U+108E8 TETH
- U+108E9 YODH
- U+108EA KAPH
- U+108EB LAMEDH
- U+108EC MEM
- U+108ED NUN
- U+108EE SAMEKH
- U+108EF AYN
- U+108F0 PE
- U+108F1 SADHE
- U+108F2 QOPH
- U+108F4 SHIN
- U+108F5 TAW

There is no separately encoded RESH in this repertoire: U+108E3 itself is named DALETH-RESH. U+108F3 is not a researched letter identity. U+108FB–U+108FF are numbers and remain unsupported.

Authoritative Unicode reference:

- https://www.unicode.org/charts/nameslist/n_108E0.html

## Exact CAL correspondence and finite ambiguity

All uniquely named consonants map to the corresponding CAL Roman code:

| Unicode identity | CAL code(s) |
| --- | --- |
| ALEPH | `)` |
| BETH | `b` |
| GIMEL | `g` |
| DALETH-RESH | `d`, `r` |
| HE | `h` |
| WAW | `w` |
| ZAYN | `z` |
| HETH | `x` |
| TETH | `T` |
| YODH | `y` |
| KAPH | `k` |
| LAMEDH | `l` |
| MEM | `m` |
| NUN | `n` |
| SAMEKH | `s` |
| AYN | `(` |
| PE | `p` |
| SADHE | `c` |
| QOPH | `q` |
| SHIN | `$` |
| TAW | `t` |

U+108E3 is materially different from Palmyrene daleth/resh. Palmyrene Unicode has two distinct code points, so typed text is deterministic. Hatran Unicode has one character identity `DALETH-RESH`, so converting it to CAL necessarily yields the finite ordered alternatives `d` and `r`. The converter must enumerate both and must not guess from lexical context.

For the complete researched Hatran letter sequence, one U+108E3 produces exactly two CAL candidates:

- `)bgdhwzxTyklmns(pcq$t`
- `)bgrhwzxTyklmns(pcq$t`

The ambiguity metadata should identify input index 3, input character `𐣣`, and `cal_codes = ("d", "r")`.

## Attested CAL fixture

Use `klb` from CAL Hatran citation `H 71:.1 nrgwl klbˀ`:

- Unicode input: `𐣪𐣫𐣡` = KAPH + LAMEDH + BETH
- expected CAL candidate: `klb`
- provenance: H 71:.1, CAL `klb N` entry, retrieved 2026-09-07

## Bounded ambiguity

The shared converter contract limits candidate expansion to 32 per word. Repeated Hatran U+108E3 characters therefore use the existing bound:

- five ambiguous characters may produce 32 candidates;
- a sixth would require 64 and must raise `ConversionExpansionError` rather than truncate or guess.

This reuses the existing bounded-expansion invariant already established for Hebrew bare shin.

## Failure boundary

Supported:

- researched Hatran letter identities U+108E0–U+108F2, U+108F4, U+108F5;
- ASCII spaces between words;
- U+108E3 as explicit finite `d`/`r` ambiguity.

Rejected:

- U+108F3 / unverified block code points;
- U+108FB–U+108FF numbers;
- punctuation/editorial marks outside the researched letter set;
- mixed Hatran with another detected script;
- ambiguity expansions above the existing 32-candidate bound.

## Implementation implication

Add explicit `hatran` representation and `hatran_to_cal_code` strategy. Use a table whose values are ordered tuples of CAL alternatives. Most entries have one value; U+108E3 has `("d", "r")`. Conversion returns `CalCodeWordCandidates`, records `CalCodeAmbiguity` for multi-valued graphemes, and calls the existing bounded `_append_alternatives`. Detection must be block-aware, while validation remains strict to the researched letter table.