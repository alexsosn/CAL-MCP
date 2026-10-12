# Agora integration handoff (released CAL-MCP v0.1.0)

CAL-MCP is a standalone local MCP server over **stdio**, not a hosted CAL-MCP service. Agora can discover, install, and launch the same upstream executable without maintaining a CAL parser or distributing CAL data. **The Agora registration is not yet implemented:** follow [Agora#222](https://github.com/alexsosn/Agora/issues/222) for the downstream registry and client-manifest change.

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

For an Agora **candidate launch record**, `uvx --from cal-mcp==0.1.0 cal-mcp` expresses the pinned local stdio executable. This is a proposed metadata shape, **not yet verified as an Agora-generated Claude/Codex configuration**. Agora must generate its native manifests from canonical registry sources, test both relevant launch paths, and report platform/client verification separately. Other launchers may use a managed Python environment with `cal-mcp==0.1.0` and the `cal-mcp` executable; no Agora runtime code should alter CAL-MCP semantics.

Startup, `--version` and MCP `list_tools` can verify launch and discovery **without contacting CAL**. Running from the checkout is not an equivalent clean-install test for the pinned package. Preserve necessary HTTPS proxy and certificate variables in the child-process environment; see [standalone proxy guidance](standalone-mcp.md#proxy-and-certificate-environments).

## One bounded, representative downstream CAL read

After verifying clean installation and stdio tool discovery offline, Agora#222 may perform **one** actual CAL read using an existing published tool and selectors already covered by the upstream fixed release smoke:

```json
{"tool": "cal_lexicon_lookup", "arguments": {"query": "br", "lemma_key": "br N"}}
```

Expected result: a schema-valid, provenance-bearing `found` lexicon record, or a truthful upstream error if CAL is unavailable. This is a **smoke test of Agora launch/reachability**, not a second upstream lexicon correctness test. It must not enumerate pages, retry unchecked, silently transform domain data, or run the entire upstream 12-case release matrix. Classify CAL failures and stop on HTTP 429 rather than treating an upstream outage as a broken Agora manifest.

The normal live client spaces transport starts by at least **3 seconds**, admits at most **8 starts per rolling 60 seconds**, and activates a **60-second** or longer cooldown after a terminal CAL 429. These are process-local protective settings, not CAL's published quota. In particular, a full 37-token passage succeeded once with completion-based waits of at least 60 seconds, but the default three-second pace previously received HTTP 429. Agora should not claim safe multi-token throughput from a single one-call smoke.

## Ownership and remaining downstream work

CAL-MCP owns its 36 tool schemas, parser behavior, bounded HTTP client, CAL-specific error classification, provenance and substantive documentation. Agora owns the canonical plugin/provider entries, version-pinned installation and launch metadata, **generated** Claude/Codex manifests, integration-only tests, and verifiable client/provider status. No CAL-MCP import of Agora, hosted CAL proxy, or duplicated lexical implementation is needed.

Upstream CAL issue [#16](https://github.com/alexsosn/CAL-MCP/issues/16) remains open until downstream [Agora#222](https://github.com/alexsosn/Agora/issues/222) is actually implemented and reviewed. Publishing this upstream handoff alone is not proof of Agora integration.
