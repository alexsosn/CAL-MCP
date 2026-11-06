# Agora integration handoff (released CAL-MCP v0.1.0)

CAL-MCP is a standalone local MCP server over **stdio**, not a hosted CAL-MCP service. Its [registration PR #268](https://github.com/alexsosn/Agora/pull/268) **merged into Agora main** on 4 November 2026, completing downstream [Agora#222](https://github.com/alexsosn/Agora/issues/222). Agora's canonical registry now includes CAL-MCP in its **candidate v1.1** marketplace scope; that marketplace release is **not yet published**. Standalone CAL-MCP remains independently installable, and Agora distributes neither a CAL parser nor CAL data.

## Upstream release identity

| Field | Released contract |
| --- | --- |
| Python package | `cal-mcp==0.1.0` |
| GitHub release | [v0.1.0](https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0) |
| Release source commit | `d8aa7fe269198ee37b4da8d71f5ed2f7eb5fe1fb` |
| Minimum Python runtime | Python 3.11 |
| Local command / arguments | `cal-mcp` / none |
| MCP transport | stdio |
| Software license | MIT |
| Data mode | remote; CAL is queried on demand |
| Data rights and service terms | upstream-dependent |

The tagged [release workflow](https://github.com/alexsosn/CAL-MCP/actions/runs/38178217487) passed clean wheel/sdist installation, frozen tool/schema checks, bounded installed-wheel smoke, and PyPI publication. The **36 public tools** span lexicon, text retrieval, token analysis, searches, concordances, bibliography, Targum and Syriac research. The executable MCP schemas and [public capability matrix](../index.md) are authoritative; Agora must not invent additional CAL tools or present the local stdio process as hosted HTTP/SSE.

CAL-MCP software installs without any CAL text or lexicon data. CAL-backed operations require outbound HTTPS to [CAL](https://cal.huc.edu/). CAL content and individual source editions may carry separate upstream-dependent rights and service restrictions; the MIT software license does not authorize downstream redistribution of those data.

## Installation and launch boundaries

A standalone installation requires no Agora:

```bash
python -m pip install "cal-mcp==0.1.0"
cal-mcp --version
```

The merged Agora registration generates Claude and Codex plugin manifests from canonical metadata. Both launch the published local stdio executable with `uvx --from cal-mcp==0.1.0 cal-mcp` plus a constraints file: Claude's manifest passes `--constraint ${CLAUDE_PLUGIN_ROOT}/runtime-constraints.txt` (expanded by the client), while Codex's manifest passes `--constraint runtime-constraints.txt` with working directory `plugins/cal`. The constraints pin `cal-mcp==0.1.0`. The candidate release scope is `registry/v1.1.yaml`, separate from Agora's frozen v0.1 contract. Other launchers may use a managed Python environment with the same published package and `cal-mcp` executable; no Agora runtime code should alter CAL-MCP semantics.

**Client verification is asymmetric:** the generated **Codex** stdio path is **verified** by a bounded real CAL lookup, including discovery of all 36 published tools; the generated **Claude** path has deterministic manifest checks but no recorded live CAL lookup and remains **community**. Agora's aggregate CAL plugin status is community. The upstream CAL endpoint's long-term availability and the exact number of HTTP starts for that one lookup were not independently measured. Merging the metadata does not publish Agora marketplace v1.1.

Startup, `--version` and MCP `list_tools` can verify launch and discovery **without contacting CAL**. Running from the checkout is not an equivalent clean-install test for the pinned package. Preserve necessary HTTPS proxy and certificate variables in the child-process environment; see [standalone proxy guidance](standalone-mcp.md#proxy-and-certificate-environments).

## One bounded, representative downstream CAL read

Agora's integration exercised **one** published CAL lexical operation with the same fixed selectors as the upstream release smoke (see bounded generated-Codex [live run 38234918961](https://github.com/alexsosn/Agora/actions/runs/38234918961) and follow-up [run 38235243021](https://github.com/alexsosn/Agora/actions/runs/38235243021)):

```json
{"tool": "cal_lexicon_lookup", "arguments": {"query": "br", "lemma_key": "br N"}}
```

The observed live operation returned a provenance-bearing `found` lexicon record. Later downstream deterministic regression tests additionally reject mismatched lemma keys, empty headwords, spoofed CAL URLs and timezone-naive provenance, but those stricter assertions were not exercised against CAL in the earlier live runs. The smoke tests Agora launch/reachability; it does not certify all CAL lexical behavior or remote uptime. Do not enumerate pages, retry unchecked, silently transform domain data, or run the upstream 12-case release matrix merely to verify Agora. Classify CAL failures and stop on HTTP 429 rather than treating an upstream outage as a broken Agora manifest.

The normal live client spaces transport starts by at least **3 seconds**, admits at most **8 starts per rolling 60 seconds**, and activates a **60-second** or longer cooldown after a terminal CAL 429. These are process-local protective settings, not CAL's published quota. In particular, a full 37-token passage succeeded once with completion-based waits of at least 60 seconds, but the default three-second pace previously received HTTP 429. Agora should not claim safe multi-token throughput from a single one-call smoke.

## Ownership and remaining downstream work

CAL-MCP owns its 36 tool schemas, parser behavior, bounded HTTP client, CAL-specific error classification, provenance and substantive documentation. Agora owns the canonical plugin/provider entries, version-pinned installation and launch metadata, **generated** Claude/Codex manifests, integration-only tests, and verifiable client/provider status. No CAL-MCP import of Agora, hosted CAL proxy, or duplicated lexical implementation is needed.

Downstream [Agora#222](https://github.com/alexsosn/Agora/issues/222) is closed after the reviewed and merged [PR #268](https://github.com/alexsosn/Agora/pull/268). This guide records the completed scope of upstream CAL issue [#16](https://github.com/alexsosn/CAL-MCP/issues/16). An Agora marketplace v1.1 publication, additional client-specific live evidence and any future CAL package release have their own verification gates; they are not implied by the repository merge.
