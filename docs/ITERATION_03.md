# Iteration 3 — impact-first diagnosis and narrow vanilla guards

Date: 2026-10-30. RimDiag 0.3.0; parser 3 unchanged, impact rules version 1. This iteration adds an optional source-only local patch beside the read-only MCP. It does not give the MCP source-reading, execution or patch-installation tools.

## Scope and permissions

The user explicitly declined third-party implementation access. Only workspace code, current vanilla code and the user-named `LocalReadingPolicyNullGuard` were inspected. Third-party About metadata/log references remain diagnostic data; installed Harmony is a build reference, not decompiled implementation. No third-party Source/Defs/Patches were read or DLLs decompiled. No normal save or Mod configuration was changed.

## Diagnosis change

The previous symptom summary sorted by frequency. That could bury a once-only mandatory initialization failure beneath recurring warnings. A null `thingClass` on furniture is structurally invalid input: the vanilla reading-policy constructor traverses **all** ThingDefs and uses an unguarded Book type predicate. A furniture label does not make the error cosmetic.

`rimdiag_prioritize` scans every retained occurrence, including later occurrences sharing a headline. It ranks mandatory initialization paths, structural runtime-class defects, exhausted generation retries and patch/initialization failures. It returns evidence-ready group/occurrence handles and lines. The first triage page includes priorities and structural leads; the CLI MCP client selects evidence by these handles. No errors are hidden or automatically attributed.

Caller-supplied observed blockers can reference existing groups using a typed report. Such reports are explicitly external, not independently verified, and apply to the current call only. The original logged impact remains attached when reported priority is raised. A successful workaround does not mean the original definition is repaired. Reporter “Likely cause” hints are excluded from impact evidence.

Real MCP replay of the retained 615-package log still reports 103 candidates / 68 exact groups / 44 symptom families. Without a caller report, the later Pawn generation/creation failures lead the current-log ranking; the four structural furniture leads remain visible separately. With the user's observed map-entry blocker report, the referenced furniture groups lead with explicit user-report provenance. This avoids inventing a historical reading exception that is absent after an existing guard already took effect. The user independently reported that their existing reading guard restored map entry; this is not our new gameplay test.

## Patch: current vanilla consumers only

[Source and instructions](../patches/LocalIntegratedVanillaGuards/README.md).

- Current vanilla: **1.7.4990 rev1069**, `Assembly-CSharp.dll` SHA256 `4E61D57205944C113631234BC55136A1A7C1679667B26008BEE5425BCFFA1463`.
- Reading: one Book predicate made null-safe; the existing named guard is detected and retained.
- Appearance: `Graphic_Appearances.MatSingle` returns actual vanilla BadMat for missing default subgraphics only. Valid defaults execute the original getter.
- Unknown build, wrong getter structure or conflicting patch composition refuses installation. Separate module outcomes are explicit; only owned registrations on the corresponding target are removed on installation failure.

Important timing finding: vanilla `PlayDataLoader` resolves Def/icon references before startup static constructors. The appearance guard therefore installs in the Mod constructor. A late static bootstrap would miss the initial failure. Reading protection installs later to recognize the pre-existing guard.

The original asset/Def producer behind the graphical failure is not proven. An actual MCP repair-plan review matched both retained log anchors but returned **needs_evidence** for the unresolved fault-origin hypothesis. Runtime containment is not a verified root-data repair or publication approval.

## Validation levels

| Level | Evidence | Scope |
|---|---|---|
| Offline Python | 62 unittest checks, including real stdio discovery/denials, typed priority tool, first-page integration and impact regressions | Diagnosis behavior and permission boundaries; no gameplay |
| Real-reference compilation | Main guard and separate live fixture build against current 1.7 vanilla/Harmony, zero warnings/errors | Compilation only; no 1.6 references available |
| Offline current-reference harness | 28 checks: null/non-null type behavior, exactly-one operand rewrite, absent/double anchor refusal, default-array checks, getter shape/refusal, real Harmony registration/removal, hash acceptance, existing guard identity and unknown composition refusal | Does not initialize engine BadMat |
| Live engine, disposable inherited profile | Actual missing-default getter returns engine BadMat; healthy synthetic child called exactly once by original getter; existing reading guard delegated | Synthetic material checks plus startup readiness, not furniture placement/construction/gameplay |
| Whole environment | **inconclusive**, other startup error candidates remain | No full-environment functional pass, map-generation pass or TPS improvement claimed |

Live session: `59ef53cd93a24c489a6d4fe84ee62bee`, run `35dab63eb89f48ac8990e53b8c55eca0`. Startup reached entry readiness in the private Windows desktop. Actual ordered loading matched the requested **618 packages**: 615 inherited entries, both test additions and RimProbe Agent. All five enabled DLC entries were preserved. The private `loaded-mods.json` records the complete order.

The appearance guard installed before Def resolution, then visibly handled the missing default at `Things/Building/Linked/Wall_Blueprint_Atlas`. The synthetic fixture later logged PASS. The recorded reading module delegated to `local.readingpolicynullguard`. This run contains no retained exception event whose evidence reaches `Graphic_Appearances.get_MatSingle`; that observation is not proof of fixing all graphics.

RimProbe's bounded startup scan reported 89 candidates, while RimDiag recognized 60 events / 46 groups / 33 families in that stdout log. These are different heuristics, not comparable scores. The older 103-event native log includes a different execution path, generation attempts and developer checks: **do not interpret 103 → 60 as errors fixed**. The live stdout used CP936; strict conversion to a private UTF-8 derivative preserved raw bytes/provenance and yielded zero decoding-replacement lines. No automatic encoding guessing was added to the MCP.

Cleanup succeeded; owned-process exit was verified, with no forced stop reported. Background monitoring recorded 2,069 focus samples, zero observed foreground violations and no system input injection; sampling does not prove absence of every transient event. The normal ModsConfig SHA256 remained unchanged. The temporary fixture directory was removed after exact file verification. The new independent guard directory remains installed but was **not enabled in the normal player configuration**. Existing reading guard files were retained.

Private logs, repair plan/review, profiles, checksums and actual loaded order remain under ignored `runs/`; they are not published. Source-only repository changes do not include game/Harmony assemblies or generated binaries.

## Remaining limitations / 后续边界

没有修复第三方家具实现、资源包、Pawn 生成约束、Harmony 参数绑定、锚点失配或无效 IL；不能从调用栈猜包归责，更不能靠全局吞异常让日志变干净。默认子图保护只覆盖该 getter，不覆盖所有绘制路径。没有测试真实家具放置、建造、供材、读档或性能；1.6 仍只有文本诊断能力，本次补丁未编译或实测 1.6。

本轮交付的是经过限定验证的本体侧保护和更合理的调查优先级。具体第三方根因、完整功能与发布质量仍需获得适当授权后的调查及作者真人实测。
