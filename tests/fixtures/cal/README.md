# CAL parser fixtures

These fixtures are deliberately reduced semantic excerpts, not archived CAL pages. They retain only the minimum current markup/text relationships needed by offline parser tests.

Capture/recheck date: **2026-09-04**.

| Fixture | CAL source | Purpose |
| --- | --- | --- |
| `browse_b.html` | `https://cal.huc.edu/browseSKEYheaders.php?first3=%22b%22` | direct headwords, homographs, alias-arrow resolution |
| `entry_br_n.html` | `https://cal.huc.edu/cal_entry_web.php?lemma=br+N` | numbered/nested senses, dialects, Unicode citation text, form/usage, derivative depth, notes |
| `entry_bysh_n.html` | `https://cal.huc.edu/cal_entry_web.php?lemma=by%24h+N` | full-form alias resolution and optional-section absence |
| `entry_nmy_x.html` | `https://cal.huc.edu/oneentry.php?cits=all&lemma=nmy+X` | unnumbered primary sense, nested sense, notes |
| `entry_abr_v.html` | `https://cal.huc.edu/oneentry.php?cits=all&lemma=%29br+V` | root cross-reference and stem-specific verb senses |
| `not_found.html` | CAL lexicon surface | explicit no-match semantic page |

The reduced excerpts are maintained only as test contracts. Normal tests make zero CAL requests. If current CAL markup materially changes, update the fixture provenance and parser tests rather than silently accepting incomplete output.
