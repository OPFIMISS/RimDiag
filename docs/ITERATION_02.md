# Iteration 02: real-log MCP diagnosis / 真实日志驱动迭代

Date: 2026-10-30. Version 0.2.0, parser version 3. This iteration reads existing logs and identity metadata only. No new game launch, game assembly compilation, Mod implementation reading, decompilation, patch application or player-config edit occurred.

## Actual inputs and method

Two native 1.7 logs and a red-line export were copied to private stable inputs. Actual MCP stdio calls exercised capabilities/analyze/triage, category-filtered groups, evidence, exact-package inventory and comparison. About metadata was read from the installed Mods library, Workshop library and game Data; Source, Defs, Patches and DLL contents were not read. The configured list contains 615 packages. All have metadata matches; one active package identity has duplicate installations and remains ambiguous. Configured order is not verified actual-loaded order.

The same current metadata/config snapshot was supplied to both historical native logs. It is not proof that both original game processes used that exact environment. Player ModsConfig bytes still match the frozen input after this work. Private inputs and evidence are not uploaded.

## Problems found and changes

| Observation | Change |
|---|---|
| Full `YYYY-MM-DD HH:MM:SS.mmm` prefixes were retained, producing false differences | Separate known date/time, severity, vanilla logger and selected thread prefixes; preserve raw evidence and unknown tags |
| Inner exception lines and end-of-chain markers were counted independently | Attach continuation/inner exception/end markers to the active event before error detection; preserve the chain and bounded exception type list |
| INFO diagnostics containing the word “error” and reporter commentary were miscounted | Separate counters for non-error-severity keyword matches and diagnostic annotation lines; annotations remain unverified, not root-cause findings |
| A reporter's `[Likely: ...]` label could contaminate identity matching | Extract balanced nested labels as unverified `reported_attributions`; remove these guesses from identity-matching input |
| First pages were dominated by repeated kinds of symptoms | Add indexed symptom families, category counts, filters and frequency sorting; preserve every exact headline group and occurrence |
| Looking up a known package required paging hundreds of entries | Add exact `inventory(package_id=...)` lookup with About-backed display name, versions and declared dependency activation |
| Comparison hashes alone forced extra retrieval | Include bounded titled new/disappeared examples with evidence-ready group IDs |
| A red-line export mixes multiple historical sections | Expose date-stamped section markers and a historical/upstream-truncation warning; do not silently select or suppress sections |
| Parser rule changes make counts incompatible | Record parser versions, refuse cross-version comparisons and require reanalysis; legacy evidence remains readable |

An intermediate replay also caught a case-insensitive severity parser removing the sentence word “Error” from “Error while instantiating”. A regression now preserves sentence text; bare severity tokens are uppercase, bracketed severity remains case-insensitive. Intermediate parser-2 snapshots are retained locally and excluded from final acceptance.

## Same-input before/after

These are **parser observations, not repaired game errors**. The old version splits exception chains and includes commentary; a lower count is not a successful game run.

| Input | Bytes / lines | 0.1 event candidates / groups | 0.2 event candidates / exact groups / symptom families |
|---|---|---|---|
| Current Player.log copy | 1,205,338 / 12,788 | 188 / 124 | 95 / 64 / 40 |
| Previous native log copy | 1,218,552 / 12,897 | 197 / 127 | 104 / 70 / 44 |
| Red-line export | 77,832 / 334 | 190 / 92 | 190 / 92 / 28 |

Both native logs retain 48 diagnostic annotation lines and 11 keyword hits at non-error severity as separate counters. No retained event/physical-line truncation or decode replacements were observed for these inputs. The export has eight date-stamped section markers; its last marker does not prove complete coverage of the latest startup, and a byte-complete scan does not restore excerpts already shortened upstream.

Native-log comparison changed from 30 shared / 97 baseline-only / 94 candidate-only groups to **58 shared / 12 baseline-only / 6 candidate-only** after correcting parsing. These are exact-headline differences, not 6 independently established new defects or evidence of who caused them. No shared error was suppressed. Unknown game binaries/assets/configuration history prevent a same-environment or causal claim.

The current native log still contains initialization/Harmony failures, missing types, Def validation issues and language-not-ready errors. One historical exported missing-type family accounts for 34 events across 17 exact groups, but that same family is absent from the current native error groups. This demonstrates why a historical export must not automatically drive repairs to the current installation. Exact package lookup resolved an ID literally present in the export to About metadata and dependencies without reading implementation; support-version metadata alone does not establish compatibility or blame.

## Context cost observations

For the final current native snapshot, JSON UTF-8 payload sizes were **808 bytes for summary** and **2,663 bytes for top-three-family triage**. This excludes MCP transport overhead and is not a client token measurement or diagnosis-accuracy benchmark. Detailed evidence is fetched only on request; it is not dumped to the console by the one-pass client.

The repeatable synthetic benchmark still checks 600 identities and 10,000 repeated errors. One 0.2 observation: 1.218 seconds, 806-byte summary, 578-byte first group page and 613-byte selected evidence. Timings depend on hardware/input; no Flash-model matrix or real-world attribution accuracy was measured.

## Validation and reproduction

- 46 local unittest cases pass, including real SDK stdio, new triage/filter tools, full-date normalization, exception chains, reporter isolation, Def symptom grouping, exact-package lookup, section warnings and parser mismatch refusal.
- `pip check` and compileall pass. Source installation and wheel checks are separate from game-runtime compatibility; no RimDiag live-game adapter exists.
- `scripts/diagnose.py` successfully drove the real MCP service against both native copies and saved private comparison/evidence. This starts the Python service only, never the game.
- No-error parsing is never a functional pass; all reports remain `functional_status=not_tested`.

```powershell
& ./.venv/Scripts/python.exe -m unittest discover -s tests -q
& ./.venv/Scripts/python.exe -m pip check
& ./.venv/Scripts/python.exe -m compileall -q src tests scripts
& ./.venv/Scripts/python.exe scripts/benchmark.py
& ./.venv/Scripts/python.exe scripts/diagnose.py --store ./runs/check `
  --log 'D:/Logs/Player-prev.log' --log 'D:/Logs/Player.log'
```

To resolve identities, supply actual `--mods-config` and repeatable `--mod-root` options from the README. Those authorize identity metadata only. Logs/metadata remain untrusted data; the third-party implementation permission boundary is unchanged.

Local final native snapshots: `3f59ee051e2243d591d42c8f6b6ef153` (previous), `3f2bba379a534cdda1d021f0760b88ae` (current); red export: `66ffbec2a3dc4edb8b5cba8b824fffcd`. These identify private local evidence, not downloadable repository files. Original failed/partial replay attempts are retained; they do not count as acceptance.

## Remaining work

More real 1.6/localized formats, log phase/actual-load provenance, validated runtime-object or assembly identity without implementation access, dependency-aware controlled experiments and independent effects remain future work. Section markers are a warning, not a complete session selector. This version cannot prove the responsible Mod or generate a verified compatibility patch from a namespace alone. No new release binary is published; distribution remains source preview.
