# 设计文档协调 (Design Coordination)

参考: Compound Engineering design workflow (知识库优先 + 渐进细化 + 跨关注点扫描) +
      BMAD design methodology (ADR 驱动 + 人类决策 + 知识沉淀)

## 核心理念

设计阶段的目标不是写一份完美的文档，而是**做出一组可辩护的技术决策**。你在协调这个过程——人类做关键决策，你负责信息聚合、交叉检查、审查编排和知识沉淀。

**设计文档是开发阶段的唯一技术事实源。** 代码实现必须能回溯到设计决策。

## 协调流程 (5 步)

### 第 1 步: 知识库优先 (Knowledge Base First)

**目标:** 在开始设计之前，先理解已有的约束和可复用的模式。不做重复决策，不违反已建立的架构原则。

**查询清单:**

| 查询目标 | 在知识库中的位置 | 要回答的问题 |
|---------|----------------|-------------|
| 架构决策 | `knowledge-base/decisions/ADR-*.md` | 哪些已有决策会约束本次设计？ |
| 可复用模式 | `knowledge-base/patterns/` | 有没有已经解决过类似问题的模式？ |
| 经验教训 | `knowledge-base/lessons/` | 过去类似场景踩过什么坑？ |
| API 契约 | `knowledge-base/api-contracts/` | 有哪些 API 契约不能破坏？ |
| 需求规格 | `requirements/{id}.md` | 需求的具体约束是什么？ |
| 头脑风暴输出 | `designs/{id}-brainstorm.md` | 推荐方向是什么？关键假设有哪些？ |

**查询后行动:**
1. 在开始设计文档前，先给人类一个简短摘要: "根据知识库，已有 {N} 个相关 ADR 和 {N} 个可复用模式。本次设计受以下约束: ..."
2. 如果有冲突——新需求与已有 ADR 矛盾——立即标记，不要默默绕过
3. 如果知识库中缺乏相关信息——记录下来，设计完成后回填

### 第 2 步: 3 阶段设计委托 (3-Stage Design Delegation)

设计阶段的核心工作由 3 个专用 Agent 依次执行。总控负责串联和验证，不直接编写设计文档。

#### Stage 1: 特性设计 (hw-feature-designer)

**委托:** Delegate to `hw-feature-designer`
**输入:** 需求规格文档 + 知识库 (ADRs, patterns, lessons) + 服务注册表 (微服务模式)
**输出:** `designs/{id}-design.md` — 跨服务特性设计文档
**验证:** 输出后调用 `feature-design-validator.md` 检查 G1-G4
**内容:**
- Section 1: 特性总览 (overview, success criteria)
- Section 2: 服务影响分析 (which services, what changes)
- Section 3: 用户旅程设计 (交互流程 + 关键时刻 + 状态矩阵)
- Section 4: 页面设计 (如涉及 UI)
- Section 5: 服务交互设计 (序列图 + SLA + 降级)
- Section 6: 跨服务契约 (OpenAPI)
- Section 7: 部署策略 (发布序列 + 特性开关 + 回滚 + 监控)
- Section 8-9: 开放问题 + 下游引用

#### Stage 2: 服务详细设计 (hw-service-designer)

**委托:** Delegate to `hw-service-designer` — 对每个受影响服务并行启动
**输入:** Stage 1 输出 (服务影响分析 + 服务交互 + 跨服务契约) + 服务注册表
**输出:** `designs/{id}-service-{service_id}-design.md` × N + `tests/api-{id}-{service_id}.json` × N
**验证:** 对每个服务调用 `service-design-validator.md` 检查 V1-V4
**内容 (后端):** S1 技术决策 → S2 架构设计 → S3 API/接口 → S4 状态管理 → S5 错误处理 → S6 安全 → S7 UT 设计 → S8 API 测试设计
**内容 (前端):** S1 技术决策 → S2 组件架构 → S3 API 集成 → S4 客户端状态 → S5 错误 UI → S6 安全 → S7 UT 设计 → S8 集成测试
**并行度:** 最多 `max_parallel_services` 个服务同时设计 (默认 4)
**模板选择:** 自动检测服务类型 (backend/frontend/bff/data-pipeline)，加载对应模板

#### Stage 3: E2E 测试设计 (hw-e2e-designer)

**委托:** Delegate to `hw-e2e-designer`
**输入:** Stage 1 输出 (用户旅程 + 服务交互 + 降级策略) + 所有 Stage 2 输出 (API 契约 + 错误处理)
**输出:** `designs/{id}-e2e-design.md`
**验证:** 调用 `e2e-design-validator.md` 检查 V1-V5
**内容:**
- 功能 E2E (每用户旅程 happy + error + boundary)
- 非功能 E2E (性能/安全/可靠性/无障碍, 按 business_domain 矩阵启用)
- 兼容性 E2E (浏览器/设备/屏幕/网络, 按 business_domain 矩阵启用)
- 自定义扩展 (按 hw.e2e_extensions 配置)

#### 阶段协调

1. Stage 1 完成 → 总控收集服务影响列表 → 启动 Stage 2 (并行)
2. 所有 Stage 2 完成 → 总控收集所有 per-service 设计路径 → 启动 Stage 3
3. Stage 3 完成 → 进入 ADR 创建和多模型验证
4. 任一步骤失败 → 回到对应步骤修订，最多 3 轮

### 第 3 步: ADR 创建 (Architecture Decision Records)

**目标:** 把设计中的重要决策沉淀为不可变的 ADR。

**创建触发条件（满足任一即创建 ADR）:**
- 决策涉及两个以上组件的交互方式
- 决策在技术选型上有实质性权衡（选 A 意味着放弃 B 的重要优势）
- 决策影响未来其他需求的设计（架构约束）
- 决策如果在 6 个月后遗忘，会导致错误的重构

**ADR 创建流程:**
1. 识别设计文档中满足触发条件的决策
2. 对每个决策，使用 `adr-template.md` 创建 ADR
3. ADR 编号自动递增（检查知识库中已有 ADR 的最大编号）
4. 写入 `{project-root}/_bmad/memory/hw-shared/knowledge-base/decisions/ADR-{NNNN}-{slug}.md`
5. 在设计文档的决策表中引用 ADR 编号

**最少要求:** 每个设计至少 1 个 ADR。如果没有任何决策值得写 ADR——那可能设计粒度太小，或者是过度工程。

### 第 4 步: 并行异质审查 (Parallel Heterogeneous Review)

**目标:** 让不同类型的审查者同时审查设计文档，发现从单一视角看不到的问题。

**审查编排:**

```
                   ┌──────────────────┐
                   │  设计文档 (草稿)   │
                   └────────┬─────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ 安全审查      │ │ 逻辑审查      │ │ 性能审查      │
    │ (Security)   │ │ (Logic)      │ │ (Performance)│
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ 安全发现      │ │ 逻辑发现      │ │ 性能发现      │
    │ P0/P1/P2/P3  │ │ P0/P1/P2/P3  │ │ P0/P1/P2/P3  │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           └────────────────┼────────────────┘
                            ▼
                   ┌──────────────────┐
                   │  问题汇总 + 分类   │
                   └────────┬─────────┘
                            ▼
                   ┌──────────────────┐
                   │  冲突检测 + 人类   │
                   │  裁决（如有冲突）  │
                   └──────────────────┘
```

**审查维度:**

| 审查者 | 重点关注 | 阻塞级别 |
|--------|---------|---------|
| 安全审查 | 认证/授权漏洞、数据泄露风险、输入校验缺失、敏感数据暴露、审计追踪缺失 | P0/P1/P2 |
| 逻辑审查 | 状态机遗漏、边界条件、并发问题、错误处理完整性、数据一致性 | P0/P1/P2 |
| 性能审查 | N+1 查询、缓存策略、连接池配置、资源泄漏、可扩展性瓶颈 | P0/P1/P2 |
| 人类 | 架构合理性、业务对齐、战略方向、冲突裁决 | 最终决策 |

**并行执行规则:**
- 安全、逻辑、性能三个审查同时启动（互不依赖）
- 每个审查者只拿到设计文档的路径（不是内容），自己去读
- 审查结果写入 `{project-root}/_bmad/memory/hw-shared/reviews/{design-id}-review-{type}.md`

**审查结果汇总:**

| 审查者 | P0 | P1 | P2 | P3 | 状态 |
|--------|----|----|----|----|------|
| 安全 | {N} | {N} | {N} | {N} | PASS/FAIL |
| 逻辑 | {N} | {N} | {N} | {N} | PASS/FAIL |
| 性能 | {N} | {N} | {N} | {N} | PASS/FAIL |

### 第 5 步: 冲突解决与收敛 (Conflict Resolution & Convergence)

**目标:** 解决审查发现的问题和审查者之间的冲突。

**问题处理优先级:**

| 级别 | 行动 | 时限 |
|------|------|------|
| P0 | 立即修复，重新审查受影响章节 | 进入下一阶段前 |
| P1 | 必须修复，设计修订后确认 | 进入下一阶段前 |
| P2 | 必须修复，可以进入下一阶段后并行处理 | 实现开始前 |
| P3 | 记录，不阻塞 | 不限 |

**审查者冲突处理:**
如果两个审查者的建议互相矛盾（如: 安全要求加密 → 性能担心加密开销）:

1. **记录冲突:** 写入 `{project-root}/_bmad/memory/hw-shared/reviews/{design-id}-conflicts.md`:
   ```markdown
   | # | 冲突 | 审查者 A | 审查者 B | 影响 |
   |---|------|---------|---------|------|
   | 1 | {描述} | 安全: {观点} | 性能: {观点} | {如果各自采纳的后果} |
   ```

2. **呈现选项给人类:**
   - 选项 A: 采纳审查者 A 的建议（附后果）
   - 选项 B: 采纳审查者 B 的建议（附后果）
   - 选项 C: 折中方案（如果你能想到）
   - 选项 D: 自定义方案

3. **记录决策:** 写入 `{project-root}/_bmad/memory/hw-shared/design-decisions.md`，关联 ADR 编号。

## 可追溯性矩阵 (Traceability)

设计完成时，必须建立从需求到设计决策再到任务的追溯链:

| 需求 AC | 设计决策 | 实现任务 | 验证方式 |
|---------|---------|---------|---------|
| AC-1: {标准} | D-1: {决策} | Task-{id} | {测试用例} |
| AC-2: {标准} | D-2: {决策} | Task-{id} | {测试用例} |
| AC-3: {标准} | D-3: {决策} | Task-{id} | {测试用例} |

**追溯规则:**
- 每个 AC 至少被一个设计决策覆盖
- 每个设计决策至少映射到一个实现任务
- 如果某个 AC 在设计中没有对应决策 → 设计不完整
- 如果某个设计决策没有对应 AC → 过度工程，考虑移除

## 与其他阶段的集成

| 上游 | 下游 | 集成方式 |
|------|------|---------|
| 头脑风暴 | 设计协调 | 头脑风暴输出的推荐方向 + 假设/风险 → 设计的技术决策种子 |
| 需求规格 | 设计协调 | 需求 AC → 设计决策 → 任务拆分 |
| 设计协调 | 任务拆分 | 设计完成后的组件/接口 → 分解为 tasks.yaml |
| 设计协调 | 知识库 | ADR 写入 + 新模式/经验教训回填 |

## 输出产物

### 单体模式 (architecture: "monolith")

| 产物 | 路径 | 何时生成 |
|------|------|---------|
| 设计文档 | `designs/{id}-design.md` | 第 2 步完成 |
| ADR | `knowledge-base/decisions/ADR-{NNNN}-{slug}.md` | 第 3 步完成 |
| 安全审查报告 | `reviews/{id}-review-security.md` | 第 4 步完成后 |
| 逻辑审查报告 | `reviews/{id}-review-logic.md` | 第 4 步完成后 |
| 性能审查报告 | `reviews/{id}-review-performance.md` | 第 4 步完成后 |
| 冲突记录 | `reviews/{id}-conflicts.md` | 如有审查者冲突 |
| 设计决策记录 | `design-decisions.md` | 如有冲突裁决 |
| 设计门禁结果 | `designs/{id}-design-gate.md` | 所有问题解决后 |

### 微服务模式 (architecture: "microservices")

| 产物 | 路径 | 何时生成 |
|------|------|---------|
| Cross-service 设计文档 | `designs/{id}-design.md` | 第 2 步完成 (含服务交互 + 契约 + E2E) |
| Per-service 设计文档 × N | `designs/{id}-service-{service_id}-design.md` | 第 2 步 (各服务并行填充) |
| 跨服务契约 | `contracts/{service_id}-openapi.yaml` | 第 2 步 (提供方定义) |
| ADR | `knowledge-base/decisions/ADR-{NNNN}-{slug}.md` | 第 3 步完成 |
| Per-service 安全审查 × N | `reviews/{id}-service-{service_id}-review-security.md` | 第 4 步 (各服务并行) |
| Per-service 逻辑审查 × N | `reviews/{id}-service-{service_id}-review-logic.md` | 第 4 步 (各服务并行) |
| Per-service 性能审查 × N | `reviews/{id}-service-{service_id}-review-performance.md` | 第 4 步 (各服务并行) |
| Cross-service E2E 审查 | `reviews/{id}-review-e2e.md` | 第 4 步 |
| 冲突记录 | `reviews/{id}-conflicts.md` | 如有审查者冲突 |
| Per-service 门禁结果 × N | `designs/{id}-service-{service_id}-design-gate.md` | 各服务问题解决后 |
| Cross-service 门禁结果 | `designs/{id}-design-gate.md` | 全部服务 + E2E 问题解决后 |

## 过渡门禁

设计阶段完成，可以进入任务拆分阶段的条件:

### 单体模式

- [ ] 设计文档 13 个章节全部完成（design-doc-template.md）
- [ ] 至少 1 个 ADR 写入知识库
- [ ] 安全/逻辑/性能三个审查完成，P0/P1/P2 全部解决
- [ ] 可追溯性矩阵完成——每个 AC 有对应设计决策和预估任务
- [ ] 冲突（如有）已由人类裁决
- [ ] 人类确认:"设计批准，进入任务拆分"

### 微服务模式 (追加条件)

- [ ] 所有受影响服务的 per-service 设计文档完成 (`designs/{id}-service-{service_id}-design.md` × N)
- [ ] Cross-service 设计文档完成 (`designs/{id}-design.md`): 服务交互设计 + 跨服务契约 + E2E
- [ ] Per-service 审查 (安全/逻辑/性能) 全部 PASS — 每个服务的 P0/P1/P2 已解决
- [ ] Cross-service E2E 审查 PASS — E2E 用例覆盖跨服务用户旅程
- [ ] 跨服务契约文件就绪 (`contracts/{service_id}-openapi.yaml`)，提供方已签署
- [ ] Per-service 门禁全部 PASS + Cross-service 门禁 PASS
- [ ] 服务依赖图无循环，CONTRACT 类型依赖的契约路径已全部指向存在的文件
- [ ] 人类确认:"全部服务设计批准 + E2E 设计批准，进入任务拆分"

**失败处理:**
- 如果设计门禁 FAIL → 回到对应步骤修订设计，最多重试 3 轮
- 3 轮后仍未 PASS → 升级到人工决策:
  - 人类可以: (a) 手动通过门禁，标记已知风险 (b) 放弃本次设计重新开始 (c) 降级需求范围
- P0/P1 安全问题不能通过人工决策跳过——必须有具体缓解方案，即使缓解方案是"接受风险 + 记录 + 定期审查"

**完成确认语:** "设计文档完成。{N} 个 ADR 已沉淀。安全/逻辑/性能审查通过。可追溯性矩阵完整。准备好进入任务拆分吗？"
