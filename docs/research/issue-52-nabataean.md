# Issue #52 research — Nabataean Unicode → CAL code

Date: 2026-09-07

## Scope

This gate covers only the dedicated Unicode **Nabataean** block. Imperial Aramaic and Palmyrene are already implemented under separate gates; Hatran, Samaritan, Mandaic, and CPA/Syriac evidence remain separate slices.

## CAL corpus evidence

CAL exposes Nabataean lexical/corpus citations. The current CAL entry for `ˀḥr` contains Nabataean citations from `NabTomb 8:2`, `NabTomb 14:2`, and `NabTomb 30:3`.

The `NabTomb 8:2` citation begins `dnh qbrˀ ...` and is explicitly labelled Nabataean:

- https://cal.huc.edu/cal_entry_web.php?lemma=%29xr+N
- retrieval date: 2026-09-07

This gives a tiny citation-sized lexical sequence for an offline fixture without redistributing CAL text.

## Unicode repertoire

The current Unicode names list encodes Nabataean at U+10880–U+108AF. U+10880–U+1089E are letter code points. Several consonants have separate contextual final forms:

- U+10880 FINAL ALEPH; U+10881 ALEPH
- U+10882 FINAL BETH; U+10883 BETH
- U+10884 GIMEL
- U+10885 DALETH
- U+10886 FINAL HE; U+10887 HE
- U+10888 WAW
- U+10889 ZAYIN
- U+1088A HETH
- U+1088B TETH
- U+1088C FINAL YODH; U+1088D YODH
- U+1088E FINAL KAPH; U+1088F KAPH
- U+10890 FINAL LAMEDH; U+10891 LAMEDH
- U+10892 FINAL MEM; U+10893 MEM
- U+10894 FINAL NUN; U+10895 NUN
- U+10896 SAMEKH
- U+10897 AYIN
- U+10898 PE
- U+10899 SADHE
- U+1089A QOPH
- U+1089B RESH
- U+1089C FINAL SHIN; U+1089D SHIN
- U+1089E TAW

U+108A7–U+108AF are numbers, not lexical consonants, and remain unsupported. U+1089F–U+108A6 are not part of the researched letter repertoire.

Authoritative Unicode reference:

- https://www.unicode.org/charts/nameslist/n_10880.html

## Exact CAL correspondence

CAL's Roman consonant table maps the named consonant identities as follows. Contextual final forms converge to the same CAL consonant code as the ordinary form; this is deterministic normalization, not ambiguity.

| Unicode identity | CAL code |
| --- | --- |
| ALEPH / FINAL ALEPH | `)` |
| BETH / FINAL BETH | `b` |
| GIMEL | `g` |
| DALETH | `d` |
| HE / FINAL HE | `h` |
| WAW | `w` |
| ZAYIN | `z` |
| HETH | `x` |
| TETH | `T` |
| YODH / FINAL YODH | `y` |
| KAPH / FINAL KAPH | `k` |
| LAMEDH / FINAL LAMEDH | `l` |
| MEM / FINAL MEM | `m` |
| NUN / FINAL NUN | `n` |
| SAMEKH | `s` |
| AYIN | `(` |
| PE | `p` |
| SADHE | `c` |
| QOPH | `q` |
| RESH | `r` |
| SHIN / FINAL SHIN | `$` |
| TAW | `t` |

No character-level ambiguity is required for typed Nabataean Unicode because contextual forms are already distinct character identities whose consonantal values are explicit.

## Attested CAL fixture

Use the initial `dnh` sequence from CAL `NabTomb 8:2`:

- Unicode input: `𐢅𐢕𐢇` = DALETH + NUN + HE
- expected CAL candidate: `dnh`
- provenance: `NabTomb 8:2`, CAL `ˀḥr N` entry, retrieved 2026-09-07

The test fixture stores only this short sequence and locator.

## Failure boundary

Supported:

- researched Nabataean letters U+10880–U+1089E;
- ASCII spaces between words under the existing converter contract.

Rejected:

- U+108A7–U+108AF numbers;
- unassigned/reserved code points in the block;
- punctuation/editorial marks outside the researched letter set;
- mixed Nabataean with any other detected script.

## Implementation implication

Add explicit `nabataean` representation and `nabataean_to_cal_code` strategy, a table-driven 31-code-point map, block-aware detection followed by strict letter-only validation, and deterministic one-candidate conversion. Keep numbers and unverified code points fail-closed.