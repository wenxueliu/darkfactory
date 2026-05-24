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

让用户自由描述问题空间。不打断、不挑战、不进入解决方案模式。

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
6. 如果所有维度 Clear 或仅剩 `[设计时再解]` 或 `[待调研]` → 进入门禁

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

澄清完后，将收集到的信息填入 `requirements-spec-template.md` 结构，写入 `{project-root}/_bmad/memory/hw-shared/requirements/{requirement_id}.md`。

然后触发 `requirements-gate.md` 门禁检查。

## 连接到价值评估

如果需求的价值维度（用户价值/业务价值/战略对齐）仍然是 Partial，在澄清流程中调度价值评估能力:

Load `../hw-value-judgment/references/value-assessment.md`

对需求进行 5 维度评分（Impact / Effort / Risk / Dependencies / Strategic Fit），结果写入 `{project-root}/_bmad/memory/hw-shared/value-assessment/{requirement_id}.md`。

## 连接到知识库

如果在澄清过程中发现了可复用的模式、经验教训或设计决策，写入知识库:

Load `../hw-knowledge-agent/references/knowledge-update.md`

## 知识库预查询 (进入设计前)

在需求澄清完成、进入设计阶段之前，执行一次知识库快速扫描：

1. 运行知识库预查询：`python kb-search.py --scope relevant-adrs,patterns,lessons,api-contracts`（从 `references/design-coordination.md` Step 1 获取完整查询清单和命令说明）
2. 检查是否有与当前需求相关的已有 ADR、设计模式、经验教训、API 契约
3. 如果有冲突或需要参考的历史决策，在需求规格中注明，并提供知识库链接
4. 知识库查询结果作为设计阶段的输入，确保设计不会重复造轮子或偏离既有架构方向

预查询结果写入 `{project-root}/_bmad/memory/hw-shared/knowledge-base/pre-query-{requirement_id}.md`。

## 输出产物

| 产物 | 路径 | 何时生成 |
|------|------|---------|
| 需求规格 | `requirements/{id}.md` | 澄清完成后 |
| 澄清日志 | 嵌入在需求规格文件末尾 | 每次回答后增量更新 |
| 价值评估 | `value-assessment/{id}.md` | 如果价值维度 Partial |
| 知识条目 | `knowledge-base/` | 如果发现可复用知识 |
| 知识预查询 | `knowledge-base/pre-query-{id}.md` | 澄清完成后，进入设计前 |
| 门禁结果 | `requirements/{id}-gate.md` | 需求规格完成后 |
