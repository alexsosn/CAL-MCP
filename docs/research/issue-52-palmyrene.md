# Issue #52 research — Palmyrene Unicode → CAL code

Date: 2026-09-07

## Scope

This gate covers only the dedicated Unicode **Palmyrene** block. Imperial Aramaic is already implemented under its own gate; Nabataean, Hatran, Samaritan, and Mandaic remain separate research slices.

## CAL corpus evidence

CAL has Palmyrene lexical/corpus material. A current CAL lexicon entry for `qsm` contains Palmyrene citations, including PAT2743 and PAT992. The PAT992 citation contains the sequence `wlqsmyˀ` and is explicitly labelled Palmyrene:

- https://cal.huc.edu/oneentry.php?cits=all&lemma=qsm+N
- retrieval date: 2026-09-07

This is sufficient to anchor a tiny citation-sized fixture without copying a CAL page into the repository.

## Unicode repertoire

Unicode encodes Palmyrene at U+10860–U+1087F. The current Unicode chart/names list gives 23 letter code points because NUN has both ordinary and final forms:

- U+10860 ALEPH
- U+10861 BETH
- U+10862 GIMEL
- U+10863 DALETH
- U+10864 HE
- U+10865 WAW
- U+10866 ZAYIN
- U+10867 HETH
- U+10868 TETH
- U+10869 YODH
- U+1086A KAPH
- U+1086B LAMEDH
- U+1086C MEM
- U+1086D FINAL NUN
- U+1086E NUN
- U+1086F SAMEKH
- U+10870 AYIN
- U+10871 PE
- U+10872 SADHE
- U+10873 QOPH
- U+10874 RESH
- U+10875 SHIN
- U+10876 TAW

U+10877/U+10878 are fleurons and U+10879–U+1087F are numbers; they are not consonantal lexical input and remain unsupported.

Authoritative Unicode references:

- https://unicode.org/charts/PDF/U10860.pdf
- https://www.unicode.org/charts/nameslist/n_10860.html
- https://www.unicode.org/versions/Unicode16.0.0/core-spec/chapter-10/#G43540

Unicode notes that historical Palmyrene daleth/resh glyph shapes could become confused and a distinguishing dot was introduced irregularly. Crucially, Unicode nevertheless encodes **DALETH U+10863 and RESH U+10874 as distinct character identities**. Therefore typed Unicode input is deterministic even though unidentified glyph images may be palaeographically ambiguous. This converter maps characters, not images.

## Exact CAL correspondence

CAL's documented Roman consonant codes use the same named Semitic consonant identities. Mapping by Unicode character identity/name gives:

| Unicode | name | CAL code |
| --- | --- | --- |
| `𐡠` U+10860 | ALEPH | `)` |
| `𐡡` U+10861 | BETH | `b` |
| `𐡢` U+10862 | GIMEL | `g` |
| `𐡣` U+10863 | DALETH | `d` |
| `𐡤` U+10864 | HE | `h` |
| `𐡥` U+10865 | WAW | `w` |
| `𐡦` U+10866 | ZAYIN | `z` |
| `𐡧` U+10867 | HETH | `x` |
| `𐡨` U+10868 | TETH | `T` |
| `𐡩` U+10869 | YODH | `y` |
| `𐡪` U+1086A | KAPH | `k` |
| `𐡫` U+1086B | LAMEDH | `l` |
| `𐡬` U+1086C | MEM | `m` |
| `𐡭` U+1086D | FINAL NUN | `n` |
| `𐡮` U+1086E | NUN | `n` |
| `𐡯` U+1086F | SAMEKH | `s` |
| `𐡰` U+10870 | AYIN | `(` |
| `𐡱` U+10871 | PE | `p` |
| `𐡲` U+10872 | SADHE | `c` |
| `𐡳` U+10873 | QOPH | `q` |
| `𐡴` U+10874 | RESH | `r` |
| `𐡵` U+10875 | SHIN | `$` |
| `𐡶` U+10876 | TAW | `t` |

FINAL NUN and NUN deliberately converge to the same CAL consonant `n`; this is deterministic normalization of contextual glyph variants, not ambiguity.

## Attested CAL fixture

The CAL `qsm` entry contains a Palmyrene PAT992 citation with `wlqsmyˀ`. A minimal consonantal substring is `qsm`.

Encode those named Palmyrene characters directly:

- Unicode input: `𐡳𐡯𐡬` = QOPH + SAMEKH + MEM
- expected CAL candidate: `qsm`
- provenance: PAT992, CAL `qsm N` entry, retrieved 2026-09-07

The repository should record only this citation locator and expected conversion, not archive the CAL page.

## Failure / ambiguity boundary

Supported:

- U+10860–U+10876 letter identities above;
- ASCII spaces between words under the existing converter contract.

Rejected:

- fleurons U+10877/U+10878;
- numbers U+10879–U+1087F;
- punctuation/editorial marks outside the researched letter set;
- mixed Palmyrene with another detected script.

No character-level candidate ambiguity is required for typed Palmyrene Unicode. Historical daleth/resh *glyph* uncertainty is outside this text-code converter because the Unicode characters themselves distinguish the consonants.

## Implementation implication

Add explicit `palmyrene` representation and `palmyrene_to_cal_code` strategy, a table-driven 23-code-point letter map, block-aware detection followed by strict letter-only validation, and deterministic one-candidate conversion. Keep symbols/numbers fail-closed.