# 需求理解与澄清 (Progressive Clarification)

参考: Spec-Kit clarify (定义包驱动的维度扫描 + Impact×Uncertainty 前沿排序 + 增量更新) +
      BMAD guided-elicitation (自适应对话 + lead-ask-reflect-confirm + 实质完备度阈值) +
      Compound Engineering requirements-capture (问题标签 + 设计前必解 vs 设计时再解)

## 核心理念

你不是在走过一份僵硬问卷。你是在进行一次**渐进式澄清对话**。目标不是填满每个模板字段，而是**有足够的实质内容来撰写一份高质量的需求规格**。

当你有足够实质来回答以下问题时，就可以开始写需求规格了：
- 核心问题是什么？影响谁？
- 成功是什么样子？（可测量）
- 范围边界在哪里？（明确不做 > 模糊都做）
- 有哪些关键约束和假设？

## 外部能力降级协议

`sw-knowledge-agent`、`sw-grill-docs` 和 `sw-value-judgment` 是可组合的增强能力，不是本 Skill 的启动前提。调用前先检查能力是否可用：

1. 可用且调用成功 → 记录 `USED` 及其产物/摘要。
2. 不可用、超时或未安装 → 记录 `SKIPPED`，向用户输出提示，执行本地证据或剩余内部检查，然后继续流程。
3. 只有需求定义包、模板、门禁、验证器等本 Skill 内部契约无效时，才阻断流程；不能把外部 Skill 不可用直接报告为失败。

统一记录格式：

```text
⚠️ SKIPPED — {capability} unavailable.
Reason: {reason}
Impact: {missing evidence or review}
Fallback: {local evidence or remaining internal checks}
The requirement clarification continues; this is not a direct failure.
```

将记录同时加入 `Requirements Clarification Report.external_capabilities` 和规格文档的“澄清记录”（如果规格文档已经创建）。

## 执行模式 (mode)

`mode` 决定澄清是否与用户进行交互轮次：

| mode | 行为 |
|------|------|
| `interactive`（默认） | 按第 3 步的 frontier 轮次与用户往返提问，直到实质完备度阈值满足 |
| `draft` | 不发起交互轮次：基于调用方证据、tracker 与已解析上下文直接成稿 |

`draft` 模式的约束：

- 未经证据确认的决策逐条写入 `clarification.unresolved`，不得默认为已确认
- 不因缺少用户回答而跳过机器层门禁/验证器；判断层 G1–G4 对未决项按 `NEEDS_USER_INPUT` 处理，而不是判 `PASS`
- 可选能力（`sw-grill-docs` / `sw-value-judgment` / `sw-knowledge-agent`）不可用时仍按降级协议记 `SKIPPED`
- 存在未决项时结果不得为 `GATE_PASSED`，只能是 `NEEDS_USER_INPUT` 或 `READY_FOR_GATE`

## 澄清流程 (主流程 + 可选增强)

### 第 0.5 步: 定义包解析 (Document Definition Resolution)

在向用户提问之前解析 `requirements/{variant}` 定义包，确定本次使用的模板、门禁和验证器。

**确定 variant：** 调用方显式传入时直接使用；否则由 `paths.config_file` 的 `sw.business_domain` 经场景映射得到：

| business_domain | requirements variant |
|-----------------|----------------------|
| `general` | `default` |
| `fintech` | `fintech` |
| `ecommerce` | `ecommerce` |
| `internal-tools` | `internal-tools` |
| `java-springboot-enterprise` | `default` |
| 其它 / 未配置 | `default` |

**解析：** 通过统一文档定义解析器按 `paths.definition_roots`（`project → user → skill`）解析。资源逐个解析：先精确 variant，再同层 `default`——因此只声明了模板的变体（如 `fintech`、`ecommerce`）会继承同层 `default` 的门禁和验证器。显式声明但不存在的资源是配置错误，必须失败，不得静默降级到低优先级资源。

**输出：** 记录模板、门禁、验证器各自的来源 scope 与路径；第 2 步的维度扫描以解析出的模板 section 集合为基准，第 5 步执行解析出的门禁与验证器。

### 第 1 步: 理解问题空间 (Listen First)

**1.0 需求层 KB 预检 (Requirement-Level KB Pre-Check) — 可选增强，在向用户提问之前执行**

澄清阶段的 KB 预检**专注于"需求层面"的上下文**，不是"实现层面"。本地 tracker 和调用方提供的证据始终可以独立读取；`sw-knowledge-agent` 只负责补充跨知识库查询。目的有三：

| 目的 | 检出场景 | 查询目标 |
|------|---------|---------|
| **需求已实现** | 防止重复造轮子 — 避免做出已经被做过的需求 | `paths.artifact_targets.tracker` (status: done) + `paths.evidence.knowledge_roots.lessons` + `paths.evidence.knowledge_roots.patterns` |
| **需求实现冲突** | 防止新需求与已有实现矛盾（API 行为不一致、数据模型冲突、UX 不一致） | `paths.evidence.knowledge_roots.lessons` + `paths.evidence.knowledge_roots.contracts` + `paths.artifact_targets.tracker` (status: in_progress) |
| **确有已有需求的实现** | 帮助新需求继承/参考已有实现（命名一致、概念对齐、避免另起炉灶） | 已解析上下文中的领域术语 + 知识库 patterns/contracts |

**与设计阶段 KB 预检的边界：**

| 阶段 | KB 预检焦点 | 输出 |
|------|----------|------|
| **需求层（本步）** | 需求-需求关系：重复、冲突、参考 | "需求全景图" — 哪些需求已存在/在做/计划中，命名一致性、API 一致性、领域概念对齐 |
| **设计层**（澄清完成后） | 需求-实现关系：模式、契约、决策 | "实现蓝图" — 用什么模式、参考什么契约、遵循什么架构决策，确保方案与既有架构一致 |

**执行方式：**

1. **检查需求追踪器**（KB 之外的本地源）：读取配置的需求 tracker，找出所有非 `cancelled` 的需求。
   重点关注：
   - `status: done` 中标题/描述与当前需求相似的 → "需求已实现"候选
   - `status: in_progress` 中范围重叠的 → "实现冲突"候选
   - `status: planned` 中相关的 → 合并/串行机会

2. **尝试调用 `sw-knowledge-agent` (KnowledgeQuery 能力)**，按"需求层"视角查询类似需求、历史冲突教训、API 契约和领域术语。完整查询协议由该 Skill 自己维护；本 Skill 不依赖其命令、脚本或目录。
   - 可用并返回结果 → 写入“需求全景图”，标记 `USED`。
   - 不可用或调用失败 → 按“外部能力降级协议”记录 `SKIPPED`，使用 tracker、已解析上下文和调用方证据继续。

3. **生成本步输出**（"需求全景图"），写入对话上下文：
   ```markdown
   ## 需求全景图 (KB Pre-Check)

   **当前需求：** {brief description}

   ### 已实现的相关需求
   - {req-id}: {title} — {link} — {为什么相关}
   - ...

   ### 正在做的相关需求
   - {req-id}: {title} — {status} — {冲突/协同点}

   ### 已有 API 契约约束
   - {endpoint}: {summary} — {与新需求的关系}

   ### 已有领域术语（必须对齐）
   - {term}: {definition} — {新需求中的用法}

   ### 历史教训（避免重蹈覆辙）
   - {lesson}: {title} — {summary}
   ```

4. **当本步检出冲突时** — 立即告知用户，不要等到第 3 步：
   - "需求全景图显示 {req-id} 已实现 {类似功能}。请问："
     - A) 新需求替代旧需求（需明确迁移路径）
     - B) 新需求是旧需求的扩展/演进
     - C) 我没意识到旧需求的存在，请帮我看看怎么协调
   - 把这个澄清问题加入决策树，并按其依赖关系重建 frontier（即使 KB 检出了，第 3 步还是要走完）

**与 Step 1.1 的关系：** Step 1.0 结束后，你带着"需求全景图"开始 Step 1.1 的倾听 — 用户描述时，你能基于全景图追问："我看到我们已实现 {X}，这次的需求和它是什么关系？"

**记录到对话上下文**：把"需求全景图"作为后续问问题的参考。在澄清记录中也加一条 KB 预检条目。

**1.1 让用户自由描述问题空间**

不打断、不挑战、不进入解决方案模式。

**使用这些镜头倾听:**
- **Scope** — 什么在里面，什么明确在外面
- **Actors** — 谁受益，谁使用，谁决策
- **Constraints** — 不可妥协的边界
- **Success metrics** — 我们怎么知道它有效了

**何时深入追问:**
- 模糊的成功标准 ("好的用户体验") → 要求具体的度量
- 缺失的验收测试 → "你会怎么验证这确实有效？"
- 未陈述的假设 → "你认为什么是理所当然的，但可能不是真的？"

**禁止:**
- 在问题清晰之前跳到方案
- 假装熟悉你不了解的领域
- 接受 "后面再说" 作为关键细节的答案

### 第 2 步: 歧义扫描 (Ambiguity Scan)

以解析后的 `requirements/{variant}` 定义包模板的 section 集合为基准，逐项评估状态。下表是通用维度框架，不是硬性字段表：变体模板没有对应 section 的维度标注 `N/A`（例如 `internal-tools` 没有用户旅程 section），不要为它补造 section:

| 维度 | 检查内容 | 状态 |
|------|---------|------|
| 问题陈述 | 问题是否用 1-3 句话清晰描述？痛点可量化？ | Clear/Partial/Missing |
| 范围定义 | In/Out scope 是否明确？依赖项已识别？ | Clear/Partial/Missing |
| 用户故事 | 角色是否具体？每个故事有明确的价值？ | Clear/Partial/Missing |
| 用户旅程 | 至少 3 个旅程阶段？每阶段有触点/情感/成功指标？关键交互时刻已识别？异常路径已覆盖？ | Clear/Partial/Missing |
| 验收标准 | 每个 US 有 ≥ 1 个 AC？AC 可测量？ | Clear/Partial/Missing |
| 非功能需求 | 性能/安全/可用性要求已定义？有度量阈值？ | Clear/Partial/Missing |
| 约束 | 技术/时间/预算/合规约束已明确？ | Clear/Partial/Missing |
| 风险与假设 | ≥ 3 个关键假设已识别？高风险项有缓解？ | Clear/Partial/Missing |
| 价值评估 | 用户价值/业务价值/战略对齐已评估？ | Clear/Partial/Missing |
| 优先级 | 与其他需求的相对优先级？ | Clear/Partial/Missing |
| 依赖/下游 | 此需求依赖什么？什么依赖此需求？ | Clear/Partial/Missing |

**不要输出原始扫描结果给用户**（除非一个澄清问题都不会问了，那时候可以直接跳到撰写）。

### 第 3 步: 决策树与 frontier 轮次提问 (Decision Tree and Frontier Rounds)

**规则:**
- 把每个待确认决策记录为决策树节点，并记录其前置决策、影响和不确定性
- **frontier** 是所有前置条件已经确定、当前可以提问的决策集合
- 每轮一次提出**完整 frontier**，不要只挑一个问题，也不要静默遗漏同轮的独立问题
- 依赖当前 frontier 中未解决问题的后续问题必须留到下一轮
- 在当前 frontier 内按 **Impact × Uncertainty** 排序，但排序不改变完整提问范围
- 每个问题必须是多选题或简短可回答的问题，并给出推荐选项及理由
- 可检索的事实由 Agent 通过文件、代码或工具核实；只有业务判断、价值取舍和环境无法确定的决策交给用户

**问题格式:**
```
📋 [Q{n}] [维度名称]

{一句话描述为什么这个问题重要}

选项:
A) {选项 A} — {简短说明}
B) {选项 B} — {简短说明}
C) {自定义 — 用自己的话描述}

💡 推荐: {选项 X}，因为 {一句话理由}
```

同一轮重复上述格式，按当前 frontier 的排序编号。每个问题应记录 `depends_on`；没有前置依赖的问题可以出现在同一轮。

**分类标记每个问题:**
- `[设计前必解]` — 阻塞设计阶段，在进入设计之前必须确定
- `[设计时再解]` — 可以先进入设计，在设计过程中解决
- `[待调研]` — 需要外部信息/调研才能回答

### 第 4 步: 增量更新 (Incremental Spec Update)

**每收到一个答案后立即执行:**

1. 将答案编码到需求规格文件的对应章节
2. 在 `paths.artifact_targets.requirement_document` 末尾附加澄清日志:
   ```markdown
   ## 澄清记录 (Clarification Log)
   | # | 时间 | 维度 | 问题 | 答案 | 类型 |
   |---|------|------|------|------|------|
   | 1 | {ts} | {dimension} | {question} | {answer} | 设计前必解 |
   ```
3. 重新评估该维度的状态（Partial → Clear）
4. 按已确认答案重建设计树，重新计算下一轮 frontier
5. 同一轮中未回答的问题保持未决，不能默认为已确认；下一轮继续提出
6. 如果 frontier 为空且仍有 Partial/Missing 维度 → 根据新增依赖回到第 3 步
7. 如果所有维度 Clear 或仅剩 `[设计时再解]` 或 `[待调研]` → 进入第 4.5 步需求规格质询

### 第 4.5 步: 可选需求规格质询 (Spec Grilling — sw-grill-docs Quick)

在需求规格成文之后、进入正式门禁之前，**尝试委托 `sw-grill-docs` 进行 Quick 模式质询**，把规格对照项目解析后的上下文和架构决策记录（ADRs）做一次交叉验证。不可用时必须记录 `SKIPPED`，提示用户并继续内部门禁/验证器。

**为什么需要这步：**
- 澄清过程是"问用户"导向，可能漏掉项目已有的领域约束
- 用语可能与项目上下文中的术语表不一致，导致下游设计歧义
- 已有 ADR 可能已否决规格中隐含的某条架构假设

**执行方式：**

1. 尝试调用 `sw-grill-docs`（Step 0 → Step 1 → Step 2 → Phase 1 + Phase 2）:
   - **Step 0**: 由 `sw-grill-docs` 解析 `context_files` / `context_maps` / `decision_roots` / `config_file`，调用方不拼接物理目录
   - **Step 1**: 目标文档 = `paths.artifact_targets.requirement_document`（新增"需求层"调用来源）
   - **Step 2**: 深度 = **Quick**（<3 个新概念 → 术语扫描 + ADR 冲突检查）
   - **Phase 1 (Glossary Audit)**: 对照已解析上下文检查规格中每个领域术语
   - **Phase 2 (ADR Compliance)**: 对照已有 ADR 检查规格中每个架构决策

2. 接收 grill-docs 的 `Grill Docs Report`，按结果分流；如果能力不可用，按“外部能力降级协议”处理:

| Result | 行动 |
|--------|------|
| **PASS** | 零 CONFLICT、零 GAP → 执行解析后的需求门禁与验证器 |
| **CONCERNS** | 有 CHALLENGE 需要澄清 → 把 CHALLENGE 转化为决策树节点，重建 frontier，回到第 3 步 |
| **CONFLICT** | 与已解析上下文或 ADR 直接矛盾 → 立即告知用户，给出两种选择：(a) 修订规格 (b) 创建新 ADR 覆盖 |
| **SKIPPED** | `sw-grill-docs` 不可用 → 记录原因、影响、fallback 和用户提示，继续执行内部门禁/验证器；不直接失败 |

3. 在 `paths.artifact_targets.requirement_document` 末尾的"澄清记录"段追加:
   ```markdown
   | # | 时间 | 维度 | 问题 | 答案 | 类型 |
   |---|------|------|------|------|------|
   | N | {ts} | 规格质询 | sw-grill-docs Quick 报告: {PASS/CONCERNS/CONFLICT} | {response} | 设计前必解 |
   ```

**注意**:
- 规格质询不是把澄清流程重新走一遍；它针对的是"已写下的规格" vs "项目的真理来源" 这一具体冲突
- Quick 模式故意不执行 Phase 3/4 压力测试和代码交叉验证（保留给设计阶段）
- 如果没有可用的上下文或 ADR 证据 → 不把证据缺失伪装成 PASS；记录 `NOT_REQUESTED` 或 `SKIPPED` 及影响，直接进入内部门禁/验证器

## 何时停止澄清

**实质完备度阈值（不是勾选框完备度）:**
- [ ] 问题陈述: 一个不熟悉项目的人能在 30 秒内理解问题
- [ ] 成功标准: 可以客观判断 "做完了还是没做完"
- [ ] 范围边界: 明确 in/out scope，不会在开发中反复争论 "这个要不要做"
- [ ] 关键风险: 至少识别了 3 个假设或风险
- [ ] 价值评估: 能解释为什么这个需求值得做（而不是其他需求）

**已经足够好 → 进入 demand-gate（需求门禁）。**
缺失的细节可以在设计阶段补充。追求完美澄清是过度投资。

**自检:** 如果这个需求规格交给另一个开发者实现，他们会不会频繁回来问 "这个是什么意思？" 如果是 → 继续澄清。如果他们有信心独立实现 → 足够了。

## 连接到需求规格

澄清完后，将收集到的信息填入解析后的定义包结构，写入 `paths.artifact_targets.requirement_document`。

然后执行定义包中解析得到的 `gate.yaml` 和 `validator.yaml`。

## 连接到价值评估

如果需求的价值维度（用户价值/业务价值/战略对齐）仍然是 Partial，可以尝试调度价值评估能力:

尝试调用 `sw-value-judgment`; 该 Skill 可用时由它负责评估协议。不可用时记录 `SKIPPED`，提示用户缺少独立价值评估，并使用当前对话中的价值证据继续；不要因为该 Skill 不可用直接失败。

对需求进行 5 维度评分（Impact / Effort / Risk / Dependencies / Strategic Fit），结果写入 `paths.artifact_targets.value_assessment`。

## 连接到知识库

如果在澄清过程中发现了可复用的模式、经验教训或设计决策，可以写入知识库:

尝试委托 `sw-knowledge-agent`; 不可用时记录 `SKIPPED`，保留知识沉淀提议，不阻断需求澄清。

## 需求规格质询 (Spec Grilling — sw-grill-docs)

在澄清对话收敛、规格成文之后，进入设计阶段之前，对规格做一次"文档对照质询"。这是与 sw-grill-docs 的契约：

| 字段 | 取值 |
|------|------|
| 调用方 | sw-requirements-clarifier (澄清完成时) |
| 目标文档 | `paths.artifact_targets.requirement_document` |
| 深度 | Quick (术语扫描 + ADR 冲突检查) |
| 必做 Phase | Phase 1 (Glossary Audit) + Phase 2 (ADR Compliance) |
| 跳过 Phase | Phase 3 (Scenario Stress-Test) + Phase 4 (Code Cross-Reference) — 保留给设计阶段 |
| 输入 | 规格文件路径 + 需求 ID + `requirement_id` |
| 输出 | Grill Docs Report (PASS / CONCERNS / CONFLICT / SKIPPED) + inline 写入"澄清记录"段 |
| 外部能力不可用 | `SKIPPED` + 原因/影响/fallback/用户提示；继续内部门禁和验证 |

**为何选 Quick 而非 Standard/Deep：**
- 规格阶段的目的是验证"和项目已有约束是否一致"，不是设计完整性
- 场景压力测试和代码交叉验证在 sw-e2e-designer / sw-feature-designer 阶段更合适
- Quick 已足以捕获 80% 的术语/ADR 冲突，避免过度质询拖慢澄清

**与设计/规划层质询的边界：**
- 设计层（sw-grill-docs 调用源 = sw-brainstorming）：质询 design 文档
- 规划层（sw-grill-docs 调用源 = sw-strategic-planner）：质询 plan 文档
- **需求层（本节）**：质询 requirements 规格 — 这是第三种调用源

**何时跳过本步骤：**
- 项目没有任何已解析上下文或 ADR 证据，且调用方不要求本次核验 → 跳过（标注"无既有约束"）
- 规格是 trivial typo fix / 配置微调 → 跳过
- 用户明确说"快进到设计" → 跳过，但在 tracker 中记录 `grill_skipped: true`

## 知识库预查询的职责边界 (不在本 Skill 范围)

> 本节只**声明边界**：实现层预查询不由本 Skill 执行，也不写入本 Skill 的任何写入目标。

| 维度 | 需求层 (Step 1.0，本 Skill) | 实现层 (设计阶段) |
|------|------------|-----------|
| 触发时机 | 澄清开始时（提问用户之前） | 澄清完成后、开始设计之前 |
| 触发者 | sw-requirements-clarifier | sw-feature-designer 或 sw-service-designer（由服务拓扑决定） |
| 查询目标 | 需求-需求关系（重复、冲突、参考） | 需求-实现关系（模式、契约、决策） |
| 主要消费者 | 澄清对话的优先级与问题设计 | 设计的方案选择与一致性 |
| 核心问题 | "我们做过类似的吗？和它什么关系？" | "用什么模式实现？参考什么契约？" |
| 典型查询 | 查询 pattern/lesson/api/decision + tracker 状态 | 查询 decision/pattern/api |
| 输出产物 | "需求全景图"（写到对话上下文，不落盘） | 由设计阶段 Skill 自己声明写入目标（**不是**本 Skill 的写入目标） |

实现层预查询的流程、查询命令、新鲜度规则、产物路径和降级处理全部由 `sw-feature-designer` 自己维护。本 Skill 不执行它、不声明它的产物路径、也不依赖它是否已经执行。

## 输出产物

| 产物 | 路径 | 何时生成 |
|------|------|---------|
| 需求规格 | `paths.artifact_targets.requirement_document` | 澄清完成后 |
| 澄清日志 | 嵌入在需求规格文件末尾 | 每次回答后增量更新 |
| 价值评估 | `paths.artifact_targets.value_assessment` | 如果价值维度 Partial 且能力可用 |
| 知识条目 | `paths.artifact_targets.knowledge_root` | 如果发现可复用知识 |
| **规格质询报告** | **嵌入在需求规格"澄清记录"段** | **第 4.5 步质询完成后；不可用则嵌入 `SKIPPED` 记录** |
| 门禁结果 | `paths.artifact_targets.gate_report` | 需求规格完成后 |
