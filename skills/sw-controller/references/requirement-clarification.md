# 需求理解与澄清 (Progressive Clarification)

参考: Spec-Kit clarify (13维分类扫描 + Impact×Uncertainty 优先队列 + 增量更新) +
      BMAD guided-elicitation (自适应对话 + lead-ask-reflect-confirm + 实质完备度阈值) +
      Compound Engineering requirements-capture (问题标签 + 设计前必解 vs 设计时再解)

## 核心理念

你不是在走过一份僵硬问卷。你是在进行一次**渐进式澄清对话**。目标不是填满每个模板字段，而是**有足够的实质内容来撰写一份高质量的需求规格**。

当你有足够实质来回答以下问题时，就可以开始写需求规格了：
- 核心问题是什么？影响谁？
- 成功是什么样子？（可测量）
- 范围边界在哪里？（明确不做 > 模糊都做）
- 有哪些关键约束和假设？

## 澄清流程 (4 步)

### 第 1 步: 理解问题空间 (Listen First)

**1.0 知识库预检 (KB Pre-Check) — 必做，在向用户提问之前**

在开口问用户之前，先扫描项目知识库了解既有上下文。这能：
- 避免询问 KB 中已有答案的问题
- 借鉴已沉淀的模式、决策、经验教训
- 捕获可能影响需求理解的既有架构约束

**执行方式**：delegate to `sw-knowledge-agent` (KnowledgeQuery 能力)，用用户问题的关键词查询：

| 查询类型 | 适用场景 | 命令格式 |
|---------|---------|---------|
| 模式检索 | "这种需求我们做过吗？" | `python scripts/kb-search.py "<关键词>" --type pattern` |
| 决策检索 | "过去对 X 怎么决定的？" | `python scripts/kb-search.py "<关键词>" --type decision` |
| 教训检索 | "类似需求踩过什么坑？" | `python scripts/kb-search.py "<关键词>" --type lesson` |
| 契约检索 | "已有 API 怎么定义的？" | `python scripts/kb-search.py "<关键词>" --type api` |

完整命令清单与新鲜度规则见 `../sw-knowledge-agent/references/knowledge-query.md`（用 `Load` 指令加载，或委托 sw-knowledge-agent 读取）。

**记录到对话上下文**：把 KB 预检结果以"已知的相关背景"形式记录，作为后续问问题的参考。

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

对照 `requirements-spec-template.md` 的 10 个章节，逐项评估状态:

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

### 第 3 步: 优先队列提问 (Prioritized Question Queue)

**规则:**
- 最多 5 个问题在队列中（控制认知负荷）
- 每次只问 1 个问题（不要批处理）
- 优先公式: **Impact × Uncertainty** — 影响最大 × 最不确定的维度优先
- 每个问题必须是多选题或 ≤ 5 个词的简答题（降低回答成本）
- 永远给出推荐选项 + 推荐理由
- 不要提前透露后续问题（防止锚定效应）

**问题格式:**
```
📋 [维度名称]

{一句话描述为什么这个问题重要}

选项:
A) {选项 A} — {简短说明}
B) {选项 B} — {简短说明}
C) {自定义 — 用自己的话描述}

💡 推荐: {选项 X}，因为 {一句话理由}
```

**分类标记每个问题:**
- `[设计前必解]` — 阻塞设计阶段，在进入设计之前必须确定
- `[设计时再解]` — 可以先进入设计，在设计过程中解决
- `[待调研]` — 需要外部信息/调研才能回答

### 第 4 步: 增量更新 (Incremental Spec Update)

**每收到一个答案后立即执行:**

1. 将答案编码到需求规格文件的对应章节
2. 在 `requirements/{requirement_id}.md` 末尾附加澄清日志:
   ```markdown
   ## 澄清记录 (Clarification Log)
   | # | 时间 | 维度 | 问题 | 答案 | 类型 |
   |---|------|------|------|------|------|
   | 1 | {ts} | {dimension} | {question} | {answer} | 设计前必解 |
   ```
3. 重新评估该维度的状态（Partial → Clear）
4. 更新优先队列（移除已回答的，可能新增因澄清而产生的后续问题）
5. 如果队列为空且仍有 Partial/Missing 维度 → 回到第 3 步补充新问题
6. 如果所有维度 Clear 或仅剩 `[设计时再解]` 或 `[待调研]` → 进入第 4.5 步需求规格质询

### 第 4.5 步: 需求规格质询 (Spec Grilling — sw-grill-docs Quick)

在需求规格成文之后、进入正式门禁之前，**强制委托 `sw-grill-docs` 进行 Quick 模式质询**，把规格对照项目的领域模型（CONTEXT.md）和架构决策记录（ADRs）做一次交叉验证。

**为什么需要这步：**
- 澄清过程是"问用户"导向，可能漏掉项目已有的领域约束
- 用语可能与 CONTEXT.md 中的术语表不一致，导致下游设计歧义
- 已有 ADR 可能已否决规格中隐含的某条架构假设

**执行方式：**

1. delegate to `sw-grill-docs`（Step 0 → Step 1 → Step 2 → Phase 1 + Phase 2）:
   - **Step 0**: 读取 CONTEXT.md / CONTEXT-MAP.md / `docs/adr/` / `design-decisions.md` / `config.yaml`
   - **Step 1**: 目标文档 = `requirements/{requirement_id}.md`（新增"需求层"调用来源）
   - **Step 2**: 深度 = **Quick**（<3 个新概念 → 术语扫描 + ADR 冲突检查）
   - **Phase 1 (Glossary Audit)**: 对照 CONTEXT.md 检查规格中每个领域术语
   - **Phase 2 (ADR Compliance)**: 对照已有 ADR 检查规格中每个架构决策

2. 接收 grill-docs 的 `Grill Docs Report`，按结果分流:

| Result | 行动 |
|--------|------|
| **PASS** | 零 CONFLICT、零 GAP → 进入需求门禁 (`requirements-gate.md`) |
| **CONCERNS** | 有 CHALLENGE 需要澄清 → 把 CHALLENGE 转化为新问题，回到第 3 步优先队列 |
| **CONFLICT** | 与 CONTEXT.md 或 ADR 直接矛盾 → 立即告知用户，给出两种选择：(a) 修订规格 (b) 创建新 ADR 覆盖 |

3. 在 `requirements/{requirement_id}.md` 末尾的"澄清记录"段追加:
   ```markdown
   | # | 时间 | 维度 | 问题 | 答案 | 类型 |
   |---|------|------|------|------|------|
   | N | {ts} | 规格质询 | sw-grill-docs Quick 报告: {PASS/CONCERNS/CONFLICT} | {response} | 设计前必解 |
   ```

**注意**:
- 规格质询不是把澄清流程重新走一遍；它针对的是"已写下的规格" vs "项目的真理来源" 这一具体冲突
- Quick 模式故意不执行 Phase 3/4 压力测试和代码交叉验证（保留给设计阶段）
- 如果项目没有 CONTEXT.md / ADR → 跳过此步（直接进入门禁），并在规格中注明"无需质询，无既有约束"

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

澄清完后，将收集到的信息填入 `requirements-spec-template.md` 结构，写入 `{project-root}/_context/memory/sw-shared/requirements/{requirement_id}.md`。

然后触发 `requirements-gate.md` 门禁检查。

## 连接到价值评估

如果需求的价值维度（用户价值/业务价值/战略对齐）仍然是 Partial，在澄清流程中调度价值评估能力:

Load `../sw-value-judgment/references/value-assessment.md`

对需求进行 5 维度评分（Impact / Effort / Risk / Dependencies / Strategic Fit），结果写入 `{project-root}/_context/memory/sw-shared/value-assessment/{requirement_id}.md`。

## 连接到知识库

如果在澄清过程中发现了可复用的模式、经验教训或设计决策，写入知识库:

Load `../sw-knowledge-agent/references/knowledge-update.md`

## 需求规格质询 (Spec Grilling — sw-grill-docs)

在澄清对话收敛、规格成文之后，进入设计阶段之前，对规格做一次"文档对照质询"。这是与 sw-grill-docs 的契约：

| 字段 | 取值 |
|------|------|
| 调用方 | sw-requirements-clarifier (澄清完成时) |
| 目标文档 | `{project-root}/_context/memory/sw-shared/requirements/{requirement_id}.md` |
| 深度 | Quick (术语扫描 + ADR 冲突检查) |
| 必做 Phase | Phase 1 (Glossary Audit) + Phase 2 (ADR Compliance) |
| 跳过 Phase | Phase 3 (Scenario Stress-Test) + Phase 4 (Code Cross-Reference) — 保留给设计阶段 |
| 输入 | 规格文件路径 + 需求 ID + `requirement_id` |
| 输出 | Grill Docs Report (PASS / CONCERNS / CONFLICT) + 必须 inline 写入"澄清记录"段 |

**为何选 Quick 而非 Standard/Deep：**
- 规格阶段的目的是验证"和项目已有约束是否一致"，不是设计完整性
- 场景压力测试和代码交叉验证在 sw-e2e-designer / sw-feature-designer 阶段更合适
- Quick 已足以捕获 80% 的术语/ADR 冲突，避免过度质询拖慢澄清

**与设计/规划层质询的边界：**
- 设计层（sw-grill-docs 调用源 = sw-brainstorming）：质询 design 文档
- 规划层（sw-grill-docs 调用源 = sw-strategic-planner）：质询 plan 文档
- **需求层（本节）**：质询 requirements 规格 — 这是第三种调用源

**何时跳过本步骤：**
- 项目无 CONTEXT.md 且无 `docs/adr/` 目录 → 跳过（标注"无既有约束"）
- 规格是 trivial typo fix / 配置微调 → 跳过
- 用户明确说"快进到设计" → 跳过，但在 tracker 中记录 `grill_skipped: true`

## 知识库预查询 (进入设计前)

在需求澄清完成、进入设计阶段之前，执行一次知识库快速扫描：

1. 运行知识库预查询（delegate to `sw-knowledge-agent` KnowledgeQuery 能力）：
   ```bash
   python scripts/kb-search.py "<需求关键词>" --type pattern
   python scripts/kb-search.py "<需求关键词>" --type decision
   python scripts/kb-search.py "<需求关键词>" --type lesson
   python scripts/kb-search.py "<需求关键词>" --type api
   ```
   完整命令清单与新鲜度规则见 `../sw-knowledge-agent/references/knowledge-query.md`。
2. 检查是否有与当前需求相关的已有 ADR、设计模式、经验教训、API 契约
3. 如果有冲突或需要参考的历史决策，在需求规格中注明，并提供知识库链接
4. 知识库查询结果作为设计阶段的输入，确保设计不会重复造轮子或偏离既有架构方向

预查询结果写入 `{project-root}/_context/memory/sw-shared/knowledge-base/pre-query-{requirement_id}.md`。

## 输出产物

| 产物 | 路径 | 何时生成 |
|------|------|---------|
| 需求规格 | `requirements/{id}.md` | 澄清完成后 |
| 澄清日志 | 嵌入在需求规格文件末尾 | 每次回答后增量更新 |
| 价值评估 | `value-assessment/{id}.md` | 如果价值维度 Partial |
| 知识条目 | `knowledge-base/` | 如果发现可复用知识 |
| 知识预查询 | `knowledge-base/pre-query-{id}.md` | 澄清完成后，进入设计前 |
| **规格质询报告** | **嵌入在需求规格"澄清记录"段** | **第 4.5 步质询完成后** |
| 门禁结果 | `requirements/{id}-gate.md` | 需求规格完成后 |
