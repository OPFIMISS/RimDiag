# Validation / 验证记录

This page preserves **0.1.0 historical** evidence. For the current 0.2.0 / parser 3 checks and real 615-package log replay, see [iteration two](ITERATION_02.md). Historical counts must not be compared directly across parser versions.

Date: 2026-10-30. Local Windows / Python 3.10, installed MCP SDK 2.3.0 and Pydantic 2.14.1. This record distinguishes synthetic checks, historical-log replay and live-game verification.

## Offline checks

- 28 unittest cases: duplicate grouping, exact-token/path identity references, no namespace attribution, ambiguous/missing metadata, pagination, evidence truncation, long physical lines, event/byte limits, independent comparison, dependency closure, protected Core/DLC, unsafe XML, selectors, implementation-access guard, prompt-injection-as-data, per-occurrence stacks, triage and a 600-identity fixture.
- Real MCP stdio: initialize, discover eight tools, analyze, page and retrieve selected evidence; invalid run/log selectors and a nonexistent decompilation tool are checked. This is actual SDK transport, not a mock client, and not a game run.
- MCP SDK 2.3 ignores undeclared top-level argument keys: an injected source_path is discarded and cannot alter configured log input. The test verifies the log is still the one configured by the host. No claim is made that SDK rejects every extra key.
- `pip check`, compileall, editable installation and wheel build checked locally. The wheel must contain only this package and its metadata, no private logs/databases or third-party binaries.
- CI matrix is configured for Windows/Linux and Python 3.10/3.12. Configuring a job does not mean its remote execution has passed; see GitHub Actions for actual outcomes.

Reproduce:

```powershell
& ./.venv/Scripts/python.exe -m unittest discover -s tests -q
& ./.venv/Scripts/python.exe -m pip check
& ./.venv/Scripts/python.exe -m compileall -q src tests scripts
& ./.venv/Scripts/python.exe scripts/benchmark.py
```

## Synthetic scale observation

One local observation before final documentation publication, using the committed benchmark procedure:

| Metric | Observed |
|---|---|
| About identities / configured active packages | 600 / 600 |
| Repeated error occurrences / headline groups | 10,000 / 1 |
| Generated input size | 740,000 bytes |
| Analyze time including metadata inventory | 1.033 seconds |
| Default summary, JSON UTF-8 | 587 bytes |
| First group page | 536 bytes |
| One selected evidence response | 537 bytes |

This is synthetic repeated input, not 600 independent real Mod problems. Timing varies by hardware, cache and input. Byte counts exclude protocol overhead and are not measured client/model tokens. No real-world attribution accuracy, minimum trigger-set discovery or patch success rate has been measured.

## Historical real-log replay

Replayed an existing RimProbe 1.7 startup log locally, without launching the game or inspecting any third-party implementation:

- Input: 181,636 bytes / 1,869 lines, historical startup-only session `898b6f462273411d9a401f858dc9aa7d`.
- Recognized: 33 error events, grouped into 19 normalized headline groups. This agrees with that earlier run's recorded candidate counts; it is not an independent completeness/accuracy proof.
- `incomplete=false`, no input size change observed, `functional_status=not_tested`.
- No Mod inventory supplied for this replay, so no Mod identity or culprit conclusion is drawn.
- Private snapshot remains local under `runs/replay`; the original log, user paths, account information and evidence database are not published.

The historical session was run by RimProbe previously. Replaying its text does NOT establish RimDiag live-game operation, current-environment compatibility or successful diagnosis of the user's present 600+ list.

## Not validated / 未验证

No new game launch, player configuration modification, third-party source/Defs/Patches reading or DLL decompilation occurred. No game assembly compilation is needed for this Python-only project. There is no RimDiag live-game execution adapter, and no new live-game verification on either 1.6 or 1.7.

1.6-format snippets are covered synthetically; historical replay above is 1.7. Real 1.6 log corpus, more localized/custom formats, Flash-model clients, resource usage on GiB inputs, cross-platform CI outcomes and adversarial client behavior remain separate validation work. Default error recognition can miss formats and mistake diagnostic text for a candidate; no-error summaries are not passes.

## Pitfalls recorded

1. A configured package list is not the actual successfully loaded list. Report it as configured, preserve unresolved identities and require observed loading evidence for stronger claims.
2. A namespace cannot safely identify a Mod. Even a precise package/path reference only proves a reference, not responsibility.
3. Groups with identical headlines may contain different stacks. Preserve and retrieve occurrences independently; do not turn headline compression into a causal conclusion.
4. SQLite URI paths need proper file-URI escaping for Unicode, spaces and `#`; read connections close explicitly. A scale test includes this path case.
5. Do not silently truncate dependency metadata and then generate an apparently reliable isolation proposal. Oversized metadata is unreadable/unsupported; active identity gaps block proposals.
6. Keep the original severity token available when identifying events; removing `[Error]` before detection would miss unknown error messages.
7. The local default package mirror could not resolve build dependencies; the public index successfully installed the tested versions. README documents this recovery.
8. Git SSH authentication permits pushing but cannot itself create repositories. Creation requires GitHub API authentication; do not print credentials or place publication credentials in the project.
