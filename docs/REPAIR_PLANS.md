# 可审查修复方案 / Reviewable repair plans

新增 `rimdiag_review_repair_plan(run_id, plan)`。这是声明式方案检查，不是补丁执行器、自动归责器或安全认证。完整类型结构通过 MCP 工具 inputSchema 发现，源码定义在 `src/rimdiag/repairs.py`。上限：24 KiB、12 个故障链节点、24 个日志锚点、8,000 字符新补丁文本。所有字段禁止额外键。

## 必须先区分的三种角色

**发起者（trigger）**触发流程，**坏数据来源（fault_origin）**提供无效数据，**消费者（consumer）**在本体中使用它，**阻断点（blocker）**令创建游戏或其他流程失败。这些角色不能仅凭堆栈、出现时间或 Likely 标签相互替代。先前错误和后续异常可以形成调查假设；必须核对当前版本本体的数据使用路径，才能建立更强解释。

方案中的每个节点声明 `log_observation`、`external_claim` 或 `hypothesis`。日志锚点必须提供 group_id、occurrence、起止物理行和短原文；工具仅核对这些内容是否存在于已保留证据。引用存在不证明整句话正确，更不证明因果关系。截断片段以外的内容不能当作已核对证据。

本体检查使用 `vanilla_source` 外部引用：记录具体游戏版本、程序集 SHA256、位置和检查说明。工具不读取该位置，也不核验外部引用真实性；这是调用者提交、等待人工审查的声明。第三方实现权限规则保持不变，不能利用方案字段投喂未经授权代码。

## 每次修复应输出的内容

1. **故障链与证据**：发起者、坏数据、消费者和阻断点；每条明确已观察、外部声称还是假设。
2. **局部干预位置与理由**：精确目标符号与作用范围；为何选择这里；不符合预期结构时如何拒绝应用。
3. **正常行为与未解决问题**：正常输入保留何种原版行为；无效数据如何报告；原始缺失类型/坏 Def 是否仍未修复，后续功能可能怎样受影响。
4. **新补丁源码、适用版本、备份和回退**：源码仅作为惰性文本提交，不编译、不执行、不跟随路径。不修改玩家配置、存档或第三方 Mod。
5. **分层验证**：正常输入等价、无效输入行为、唯一目标匹配、方法结构不符拒绝应用等离线检查；真实引用编译；真实游戏结果。每条记录来源与证据，不能以编译替代运行。
6. **停止条件**：出现新阻断、结构不匹配、正常输入回归或清理失败时停止；保存新日志并建立新快照，继续调查。不要靠继续吞异常来制造成功。

`validation` 的来源是 `agent_report` / `author_report` / `user_report`。有结果必须附证据位置或说明；游戏启动结果必须标为 `in_game`。工具只检查声明形式，永远返回 `validation_claims_independently_verified=false`。材料齐全时是 `outline_complete_needs_human_review`，缺失时是 `needs_evidence`；二者都不是批准应用或发布。

## 用户提供的成功案例：阅读策略遇到坏家具定义

以下案例来自用户本轮叙述，**本轮未重新读取补丁、核对游戏 DLL 或复跑**。不要把用户报告转换为 RimDiag 独立完成的验证。

- 堆栈里 HugsLib 发起创建游戏，但用户调查认为实际异常发生在本体阅读策略初始化；不能直接归责发起者。
- 用户报告更早日志有类型解析失败，随后两个 ThingDef 的 `thingClass == null`。
- 用户核对对应版本本体后发现：Game 构造创建阅读策略，其初始化遍历全部 ThingDef，包括家具，并对空 thingClass 做类型判断。
- 据报告，独立 Harmony 补丁只替换该方法的一次判断为 `type != null && type.SameOrSubclassOf<Book>()`。这里是 C# 表达式；描述不足以重建可靠 Transpiler，也没有携带实际方法签名、版本构建或程序集指纹，因此仓库不据此生成通用补丁。
- 用户报告离线复现与唯一调用点、正常行为和结构不符拒绝应用检查已完成，之后亲自确认可以进入游戏。其来源应记为用户报告，实际产物尚未由本轮工具独立核验。

这个处理**隔离了某一消费者中的空值阻断，没有修复坏定义本身**。空类型家具仍可能损坏、无法实例化或在其他调用链报错；进入游戏不等于这些内容可用，也不等于存档安全。无效 Def 及其可核实包身份的诊断不能被隐藏。若移除补丁后原始数据仍坏，回退也可能重新出现原阻断。

应提炼为通用流程：坏数据 → 当前版本本体消费者 → 局部阻断 → 可验证的最小干预，而不是给 RimDiag 硬编码某个 Mod、某个 Book 判定或一个全局空值吞异常策略。

## English summary

The repair-review tool checks a bounded declarative outline: failure-chain roles, exact retained-log quotations, versioned vanilla references, a narrow intervention, unchanged normal behavior, invalid-data diagnostics, unresolved issues, newly authored inert patch text, offline/real-reference/in-game claims, backups and rollback. It never reads external source locations or executes code. Caller claims and user-reported outcomes remain unverified; a complete outline is still subject to human review.

The supplied reading-policy case is **user-reported historical evidence**, not independently reproduced here. A caller in a stack is not necessarily the fault origin. According to the report, unresolved furniture types produced null thingClass values that reached a vanilla reading-policy consumer; a single guarded predicate isolated that consumer while retaining diagnostics and normal-type behavior. The broken definitions remained broken. Do not generalize this into blanket null suppression or claim that entering the game proves content/save correctness.

Verification: 56 local tests pass, including ten-tool real MCP discovery/schema checks and repair-review tests for forged/missing quotations, wrong lines, external claims, absent validation, reported failures, strict schemas and inert source. No new game launch, vanilla assembly compilation, patch deployment or third-party implementation access occurred for this addition.
