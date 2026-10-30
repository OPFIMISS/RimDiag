# 本体侧局部整合保护 / Local vanilla guards

这是一份独立、可审查的本地补丁，**不是 RimDiag MCP 自动修复功能**。用户未授权第三方实现检查；本补丁只核对本体源码及用户指明的 `LocalReadingPolicyNullGuard`，没有读取第三方 Source、Defs、Patches 或反编译第三方 DLL。

## 适用范围与原理

仅支持当前校验过的 **RimWorld 1.7.4990 rev1069 / net10.0**。本体 `Assembly-CSharp.dll` SHA256 必须为：

`4E61D57205944C113631234BC55136A1A7C1679667B26008BEE5425BCFFA1463`

不匹配时拒绝安装，不尝试猜测兼容；没有 1.6 输出或验证。RimDiag 的文本日志诊断仍可用于 1.6 与 1.7。

| 模块 | 局部干预 | 保留的正常行为 | 没有解决的问题 |
|---|---|---|---|
| 阅读策略 | `ReadingPolicyDatabase.GenerateStartingPolicies` 中唯一的 `SameOrSubclassOf<Book>` 判断改为空类型安全判断 | 非空类型仍调用原版判断；不改 Def、不删除定义 | 家具实现缺失、其他消费者读取坏 Def |
| 默认图形 | `Graphic_Appearances.MatSingle` 默认子图数组为空、越界或对应元素为空时返回本体 `BaseContent.BadMat` | 默认子图有效时 prefix 放行，完整执行原 getter | 不恢复资源、不保护所有 Draw/SubGraphicFor 路径、不修复家具功能 |

图形保护在 **Mod 构造阶段**安装，因为 `PlayDataLoader` 的 Def/icon 解析早于启动静态构造。阅读保护在后面的启动静态构造阶段安装；如果该方法已有 `local.readingpolicynullguard`，沿用现有保护，避免重复安装。两个模块独立报告状态：一个拒绝不会撤销另一个已安装的模块。安装异常只移除本补丁在对应方法的注册，不撤销别人的补丁，也不拦截游戏全局异常。

阅读判断要求恰好一个指令锚点；图形 getter 要求与已验证的七条有效指令结构一致。发现未知阅读 transpiler 或图形 getter 已有补丁时拒绝盲目组合。仅检查安装当时的注册状态，不能保证后来其他 Mod 不再修改方法。

占位保护仍报告坏图形路径，不从路径猜所属 Mod。最多列出 32 个不同路径，之后明确提示报告上限；不会过滤原游戏错误。占位不是原始资源修复，也不是性能优化证明。

## 构建与部署

需要 .NET 10 SDK，以及本机游戏和已安装 Harmony 的引用。不要提交或分发游戏/Harmony DLL。可通过 `-p:GameDir=... -p:HarmonyPath=...` 覆盖项目中的本机默认位置。

```powershell
dotnet build patches/LocalIntegratedVanillaGuards/Source/LocalIntegratedVanillaGuards.csproj -c Release
dotnet run --project patches/LocalIntegratedVanillaGuards/Tests/Tests.csproj -c Release
```

将 `mod` 目录复制到一个**新目录** `RimWorld/Mods/LocalIntegratedVanillaGuards`，不要覆盖现有文件。保留现有 `LocalReadingPolicyNullGuard`。包 ID 为 `local.integratedvanillaguards`，依赖 Harmony，排序在 Harmony 与现有阅读保护之后。

本轮部署只添加新目录，不修改正常 `ModsConfig.xml`。在普通存档中启用前仍需作者审阅与亲自实测；建议先使用 RimProbe 的 `inherit` 一次性 profile，额外加入该包，保留原始 Mod/DLC 顺序与日志。

## 验证、备份和回退

离线 harness 使用当前本体引用，覆盖空类型判断、正常类型等价、唯一锚点、结构变化拒绝、真实 Harmony 注册与移除、已知阅读保护识别和未知组合拒绝。离线进程不初始化实际图形引擎。

`LiveProbe` 是单独的自有测试包，构建命令为：

```powershell
dotnet build patches/LocalIntegratedVanillaGuards/LiveProbe/LiveProbe.csproj -c Release
```

仅在一次性测试 profile 中加载 `fixture`（包 ID `local.integratedvanillaguards.liveprobe`）。它构造独立的测试图形对象，调用真实 getter，验证缺失默认子图返回实际引擎的 BadMat、有效子图仍被原 getter 调用一次。它不改变 Def、地图或存档，不能替代家具的放置、建造与功能测试；不要在正常配置启用此测试包。实机结果见[本轮验证](../../docs/ITERATION_03.md)。

原有 Mod 文件均不修改，原阅读保护保留；每轮 profile、原始列表摘要、实际加载列表与运行日志保存在私有 runs 目录。停止该轮自有进程后，从测试 profile 移除新增包，或移走本补丁新目录并重新启动，即可回退。不要在进程运行时热替换 DLL。

仍未修复：Pawn 生成条件互相矛盾、第三方 Harmony 参数绑定/锚点失败、第三方无效 IL、家具缺失实现。没有足够授权或本体侧安全干预依据，不能吞掉这些异常、强制生成或随意补全类型。

## English

An optional standalone local patch, separate from RimDiag's read-only MCP. It targets only the exact vanilla build fingerprint above. It does not inspect or repair unauthorized third-party implementations. The reading guard replaces one null-unsafe Book predicate, delegating to the existing named local guard when present. The appearance guard preserves the original getter for valid defaults and returns vanilla BadMat for a missing default only. This is visible fault containment, not asset or furniture repair.

The appearance module installs in the Mod constructor, before Def/icon resolution; reading protection installs later so the existing guard can be detected. Modules report independently and only remove their own target registration on install failure. Unknown method shapes/builds or conflicting patches are refused. Later third-party patching remains outside this guarantee.

Build with local .NET 10/game/Harmony references using the commands above. Deploy only to a new directory, retain the existing guard, and use disposable inherited RimProbe profiles. Do not edit normal saves or configurations. The optional live fixture checks actual engine material fallback and normal getter dispatch on synthetic objects, not furniture gameplay. See the linked validation report for offline, compilation and live-game evidence separately. Roll back by removing the additional package/directory after stopping the owned test process and restarting. No game/Harmony assemblies are distributed. No 1.6 patch support or measured performance gain is claimed.
