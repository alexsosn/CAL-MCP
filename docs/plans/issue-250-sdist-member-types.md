# Plan: refuse unsafe archive members before release installation (#250)

1. **RED:** extend the existing synthetic sdist archive helper and tests to
   construct a safe-named symlink to an absolute target, a hardlink whose
   target contains `..`, a FIFO member and a directory. For each unsafe
   member, `_find_distributions` must raise a controlled `RuntimeError`
   identifying an unsupported member type before any installation.
   A harmless root directory and regular files must remain valid.
   Retain existing duplicate metadata / embedded version mismatch tests.
2. **GREEN:** in `_sdist_version`, after member-name path safety, reject
   members unless `member.isfile() or member.isdir()`. No extraction,
   no change to installation or tool contracts.
3. Execute Ruff check/format, strict mypy and pytest under both pinned and
   latest-compatible CI matrices on the final head.
4. Logically independent adversarial review on exact final SHA must examine
   tar member types, bogus regular-file metadata, path traversal, and
   genuine built-artifact compatibility. Do not merge without review and CI.
5. Existing tag-free build/install rehearsal from `main` passed; if this
   change affects real packaging semantics, re-run a single offline
   tag-free artifact rehearsal. No CAL load, tags, publishing or Agora work.
