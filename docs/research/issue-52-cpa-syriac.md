# Issue #52 research — CPA/Syriac Unicode conversion edges

Date: 2026-09-07

## Scope

CPA (Christian Palestinian Aramaic) is not assigned a separate Unicode script block. Its ordinary encoded text uses characters in the Unicode Syriac block, so CPA must remain on the existing `syriac` representation/strategy rather than inventing a dialect-specific Unicode representation.

This gate audits the Syriac letter inventory for CAL-relevant finite ambiguity and CPA-specific characters that the first consonantal table did not cover.

## CAL corpus evidence

CAL has a distinct CPA dialect family and current CPA corpora. A current CAL lexical citation provides a tiny offline fixture:

`CPAHor 407:3 ܕܝܢ ... dyn ...`

from the entry for `lˀ klwm`:

- https://cal.huc.edu/oneentry.php?cits=all&lemma=l%29%40klwm+R
- retrieval date: 2026-09-07

The fixture `ܕܝܢ → dyn` is enough to prove that ordinary CPA consonants use the same Syriac conversion path.

CAL's Text Entry and Format Manual also states that the emphatic `P` (= Greek pi) of Christian Palestinian Aramaic is represented by the same code used for emphatic/final peh. The current live CAL Roman table documents `P = emphatic p`.

Sources:

- https://cal.huc.edu/pdfs/CalManualIntrol.pdf
- https://cal.huc.edu/prova.html

## Unicode CPA/Syriac evidence

The official Unicode Syriac names list explicitly identifies:

- U+0716 `SYRIAC LETTER DOTLESS DALATH RISH` — “ambiguous form for undifferentiated early dalath/rish”;
- U+0724 `SYRIAC LETTER FINAL SEMKATH`;
- U+0727 `SYRIAC LETTER REVERSED PE` — “used in Christian Palestinian Aramaic”.

The Unicode core specification further says:

- before pointing, early Syriac did not distinguish dalath and rish; U+0716 encodes that ambiguous form;
- U+0723 SEMKATH and U+0724 FINAL SEMKATH are common variants and may occur interchangeably in the same document;
- U+071E YUDH HE is a ligature-like unique character, mostly used in East Syriac texts.

Authoritative references:

- https://www.unicode.org/charts/nameslist/n_0700.html
- https://unicode.org/versions/Unicode17.0.0/core-spec/chapter-9/

Unicode Technical Note 52 on Christian Palestinian Aramaic additionally records U+0716 as the CPA dalath character in its proposed CPA font repertoire and U+0727 as CPA PI. This confirms direct CPA relevance, but it does not remove the generic Unicode ambiguity of U+0716 when CAL-MCP receives only a Unicode string and no dialect metadata.

- https://www.unicode.org/notes/tn52/UTN52-Christian-Palestinian-Aramaic-Encoding-3.pdf

## Safe v0.1 decisions

### U+0716 DOTLESS DALATH RISH

The input character itself does not distinguish `d` from `r`. CAL has separate Roman codes `d` and `r`. Because the public converter receives only script text, not a CPA-vs-early-Syriac dialect guarantee, the safe deterministic contract is finite ambiguity:

`ܖ → ("d", "r")`

with `CalCodeAmbiguity` metadata at the character position. No lexical context may select one candidate.

This reuses the existing shared 32-candidate expansion ceiling: five repeated dotless characters may produce 32 candidates; a sixth would require 64 and must raise `ConversionExpansionError` before any I/O.

### U+0724 FINAL SEMKATH

Unicode explicitly states that U+0723 SEMKATH and U+0724 FINAL SEMKATH are interchangeable variants of the same letter. Therefore:

`ܤ → s`

No ambiguity metadata is required.

### U+0727 REVERSED PE / CPA PI

Unicode identifies U+0727 as used in CPA; CAL documents CPA emphatic pi with the `P` code. The existing table already contains:

`ܧ → P`

This behavior should receive an explicit CPA regression test so it remains evidence-backed rather than an unexplained table entry.

### U+071E YUDH HE

Unicode defines U+071E as a YUDH-HE ligature-like character, mostly East Syriac. I did not find a current CAL source that specifies how this single Unicode scalar should be converted to the CAL Roman code stream. Mapping it to `yh` solely from the Unicode character name would violate issue #52's no-inference rule.

Therefore U+071E remains explicitly unsupported in v0.1 pending direct CAL evidence.

### Garshuni/Persian/Syriac Supplement letters

Garshuni, Persian, Sogdian, and Suriyani Malayalam additions in the Syriac/Syriac Supplement blocks are not established as CAL Aramaic corpus characters by this research and remain unsupported.

## Attested CPA fixture

Use the current CAL CPAHor 407:3 citation:

- input: `ܕܝܢ`
- expected CAL code: `dyn`
- representation: `syriac`
- strategy: `syriac_to_cal_code`

This is citation-sized and stored only as an offline regression value.

## Implementation implication

The Syriac converter must become ambiguity-aware rather than returning a scalar string:

- ordinary researched consonants remain one-element alternatives;
- add U+0716 with ordered alternatives `("d", "r")`;
- add U+0724 as `("s",)`;
- keep U+0727 as `("P",)`;
- record ambiguity metadata and delegate expansion to the existing `_append_alternatives` helper;
- keep U+071E and marks/punctuation/unverified letters fail-closed.

No new input representation is added. This is a refinement of `syriac`, covering CPA without claiming that every Syriac-block character is supported.