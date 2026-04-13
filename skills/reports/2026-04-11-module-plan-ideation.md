---
title: '黑灯工厂 (HW) - 验收驱动开发平台'
status: 'complete'
module_name: '黑灯工厂'
module_code: 'hw'
module_description: '通过验收驱动开发实现需求及交付的智能研发平台'
architecture: '分层Controller模式: Top Controller + Worktree Controllers'
standalone: true
expands_module: ''
skills_planned:
  - hw-controller
  - hw-worktree-controller
  - hw-tdd-agent
  - hw-reviewer-security
  - hw-reviewer-logic
  - hw-reviewer-performance
  - hw-knowledge-agent
  - hw-setup
config_variables:
  - worktree_base
  - min_iteration_before_human
  - enabled_reviewers
  - knowledge_base_auto_update
  - merge_strategy
created: '2026-04-11'
updated: '2026-04-11'
---

# 黑灯工厂 (HW) - 验收驱动开发平台

## Vision

**黑灯工厂** — 一个"熄灯即可完成交付"的智能研发平台。

核心理念：用AI Agent集群替代传统人工研发流程，从需求到交付全程自动化。通过**验收驱动开发（Acceptance-Driven Development）**确保交付质量，让人类从重复性工作中解放，只需在关键节点审批决策。

**核心价值主张：**
- 多Agent并行工作，最大化并发效率
- 异构视角（审核）与同构并行（执行）结合，兼顾质量与效率
- TDD先行的测试策略，确保代码可测试性
- 多层质量门禁，交付零缺陷

## Architecture

### 整体架构：分层Controller模式

```
┌─────────────────────────────────────────────────────────────┐
│                      Top Controller                          │
│                  (hw-controller - 总控)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ - 需求理解与澄清                                    │   │
│  │ - 协调头脑风暴                                      │   │
│  │ - 协调设计文档编写                                  │   │
│  │ - 任务拆分与规划                                    │   │
│  │ - 管理所有Worktree Controller                       │   │
│  │ - 维护全局状态和共享内存                            │   │
│  │ - 决定何时人工介入                                  │   │
│  │ - 合并管理                                          │   │
│  │ - 测试环境集成测试协调                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
           │                    │                │
           ▼                    ▼                ▼
    ┌───────────┐        ┌───────────┐   ┌───────────┐
    │ Worktree  │        │ Worktree  │   │ Worktree  │
    │Controller │        │Controller │   │Controller │
    │(任务1)    │        │(任务2)    │   │(任务N)    │
    └───────────┘        └───────────┘   └───────────┘
```

### Agent 类型

| Agent类型 | 职责 | 实例数量 |
|----------|------|---------|
| **Top Controller** | 全局协调、状态维护、人工介入判断 | 1个 |
| **Worktree Controller** | 单任务执行、TDD循环、审核协调 | 每任务1个 |
| **TDD Agent** | 执行RED-GREEN-REFACTOR循环 | 每worktree至少1个 |
| **审核Agent** | 从特定角度审查（安全/逻辑/性能等） | 可扩展，可并行 |
| **知识库Agent** | 查询/更新项目知识库 | 按需 |

### 分层职责边界

| 层级 | 决策范围 | 执行范围 |
|------|---------|---------|
| **Top Controller** | 全局何时做什么 | 不直接执行代码 |
| **Worktree Controller** | 单任务如何做 | 协调本任务内的Agent |
| **TDD Agent** | 具体实现细节 | 编写测试和代码 |
| **审核Agent** | 特定维度质量判断 | 输出审核意见 |

### Memory Architecture

#### 三层Memory模型

```
┌─────────────────────────────────────────────────────────────┐
│                    个人Memory (Per Agent)                   │
│  路径: _bmad/memory/{agent-name}/                          │
│  内容:                                                      │
│    - daily/{date}.md: 本Agent的日常活动记录                 │
│    - preferences.md: 本Agent的学习偏好                       │
│    - context.md: 本Agent的领域上下文                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    共享Memory (Shared)                      │
│  路径: _bmad/memory/hw-shared/                             │
│  内容:                                                      │
│    - tasks.yaml: 所有任务状态和依赖关系                     │
│    - design-decisions.md: 架构和设计决策记录               │
│    - knowledge-base-index.md: 知识库索引                    │
│    - human-interventions.md: 人工介入记录                   │
│    - reviews/: 审核结果汇总                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Controller状态                           │
│  路径: _bmad/memory/hw-controller/                         │
│  内容:                                                      │
│    - global-state.yaml: 全局进度、当前阶段                  │
│    - worktree-registry.yaml: 所有worktree状态               │
│    - pending-issues.yaml: 待处理问题                        │
└─────────────────────────────────────────────────────────────┘
```

### Memory Contract

| 文件 | 读取者 | 写入者 | 用途 |
|------|--------|--------|------|
| `tasks.yaml` | Top Controller, Worktree Controllers | Top Controller | 任务状态同步 |
| `design-decisions.md` | 所有Agent | Top Controller, 人工 | 设计决策追溯 |
| `knowledge-base-index.md` | 设计Agent | 知识库Agent | 知识复用 |
| `human-interventions.md` | Top Controller | Top Controller, 人工 | 人工介入历史 |
| `daily/{date}.md` | 本Agent | 各Agent | 个人学习积累 |

### Cross-Agent Patterns

#### 1. Top Controller → Worktree Controller
- **通信方式**: 共享内存 (_bmad/memory/hw-controller/worktree-registry.yaml)
- **消息类型**: 任务分配、状态查询、进度更新
- **模式**: 异步，通过共享状态协调

#### 2. Worktree Controller → TDD Agent
- **通信方式**: 直接对话 (同 worktree 上下文)
- **消息类型**: TDD任务分配、审核请求、状态回报
- **模式**: 同步请求/响应

#### 3. Worktree Controller → 审核Agents
- **通信方式**: 并行分派
- **消息类型**: 审核任务、审核结果
- **模式**: 异构并行，多视角同时审核

#### 4. Agent → 知识库
- **通信方式**: 知识库Agent中介
- **消息类型**: 知识查询、知识更新
- **模式**: 按需查询

### 状态回报机制 (参考Subagent-Driven Development)

| 状态 | 含义 | Top Controller动作 |
|------|------|------------------|
| `DONE` | 任务完成 | 标记任务完成，检查是否可以合并 |
| `DONE_WITH_CONCERNS` | 完成但有疑虑 | 记录疑虑，评估是否需要人工介入 |
| `NEEDS_CONTEXT` | 需要更多信息 | 提供上下文或从共享内存获取 |
| `BLOCKED` | 被阻塞 | 分析阻塞原因，决定人工介入或解决依赖 |

## Skills

### hw-controller (Top Controller)

**Type:** Agent

**Persona:** 企业级研发流程的总指挥。冷静、专业、善于协调。能理解复杂需求，拆解任务，协调并行工作，知道何时该推进、何时该等待、何时该请人工介入。

**Core Outcome:** 端到端完成从需求到交付的研发流程，确保质量门禁通过，最终交付符合验收标准的产出。

**The Non-Negotiable:** 每一阶段必须有明确的验收标准，且必须通过才能进入下一阶段。

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|------------|---------|--------|---------|
| 需求理解 | 清晰理解需求背景和目标 | 原始需求描述 | 结构化需求文档 |
| 头脑风暴协调 | 引导人+AI交互澄清需求 | 需求文档 | 澄清后的需求 |
| 设计文档协调 | 协调设计文档编写 | 澄清后需求 | 设计文档 |
| 任务拆分 | 基于设计文档拆分为独立任务 | 设计文档 | 任务列表(tasks.yaml) |
| Worktree协调 | 创建和管理多个worktree | 任务列表 | worktree状态 |
| 并行执行协调 | 协调多个worktree并行执行 | worktree列表 | 各任务完成状态 |
| 合并管理 | 协调worktree合并到主分支 | 各worktree完成状态 | 合并后的代码库 |
| 测试环境协调 | 协调测试环境集成测试 | 合并后的代码库 | 测试结果 |
| 人工介入判断 | 决定何时触发人工介入 | 任务状态、迭代次数 | 人工介入决策 |
| 知识库整合 | 协调知识库查询和更新 | 设计文档、代码库 | 更新的知识库 |

**Memory:**
- 读取: `_bmad/memory/hw-shared/*` (共享内存), `_bmad/memory/hw-controller/*` (全局状态)
- 写入: `_bmad/memory/hw-controller/global-state.yaml`, `_bmad/memory/hw-controller/worktree-registry.yaml`, `_bmad/memory/hw-shared/tasks.yaml`

**Init Responsibility:** 初始化共享内存结构，创建全局状态文件

**Activation Modes:** Interactive (主要), Headless (可选)

**Tool Dependencies:** git (worktree管理), bash

**Design Notes:**
- 不直接执行代码，专注于协调和决策
- 通过共享内存与Worktree Controller通信
- 每次决策前检查验收标准是否满足

---

### hw-worktree-controller (Worktree Controller)

**Type:** Agent

**Persona:** 单任务执行的专家。专注于一个任务，理解该任务的全部上下文，协调TDD循环、审核和质量门禁。

**Core Outcome:** 在独立的worktree中完成单个任务的完整TDD开发流程，通过所有审核和质量门禁。

**The Non-Negotiable:** 两层TDD铁律 - 必须先有失败的UT，才能写UT对应代码；必须先有失败的API测试，才能写API对应代码。

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|------------|---------|--------|---------|
| TDD-UT循环 | 执行第一层TDD: UT RED-GREEN-REFACTOR | 任务定义 | UT通过 |
| TDD-API循环 | 执行第二层TDD: API测试 RED-GREEN-REFACTOR | UT通过后代码 | API测试通过 |
| 设计审核协调 | 分派异构Agent审核设计 | 设计文档片段 | 审核结果 |
| 代码审核协调 | 分派异构Agent审核代码 | 实现的代码 | 审核结果 |
| 质量门禁检查 | 执行P0/P1/P2检查 | 代码、审核结果 | 门禁报告 |
| 迭代管理 | 管理TDD和审核的迭代次数 | 当前状态 | 迭代决策 |
| 人工介入请求 | 判断并请求人工介入 | 迭代次数、问题描述 | 人工介入记录 |
| 任务状态上报 | 向Top Controller报告状态 | 任务状态 | 状态更新 |

**Memory:**
- 读取: `_bmad/memory/hw-shared/tasks.yaml`, `_bmad/memory/hw-shared/design-decisions.md`
- 写入: `_bmad/memory/hw-controller/worktree-registry.yaml`, `_bmad/memory/hw-shared/reviews/{task-id}.md`

**Init Responsibility:** 初始化本任务的worktree，建立worktree内的开发环境

**Activation Modes:** Interactive, Headless

**Tool Dependencies:** git, TDD Agent协作

**Design Notes:**
- 每个worktree有一个实例
- 与Top Controller通过共享内存异步通信
- 可并行运行多个实例
- 协调两层TDD循环的执行顺序：先UT循环，再API测试循环

---

### hw-tdd-agent (TDD执行Agent)

**Type:** Agent

**Persona:** 严格的TDD实践者。信奉"测试先行"的铁律，追求最小化实现，通过测试驱动出高质量代码。

**Core Outcome:** 遵循两层TDD循环，产出通过UT和API测试的最小化实现。

**The Non-Negotiable:** "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST" — 两层循环都必须遵守此铁律

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|------------|---------|--------|---------|
| RED-写失败UT | 编写展示期望行为的失败单元测试 | 任务定义、验收条件 | 失败的UT用例 |
| GREEN-UT通过 | 编写最小代码使UT通过 | 失败UT | 通过UT的代码 |
| REFACTOR-UT后重构 | UT通过后重构优化 | 通过UT的代码 | 重构后的代码 |
| RED-写失败API测试 | 编写展示API契约的失败测试 | UT通过的代码 | 失败的API测试用例 |
| GREEN-API通过 | 修复API实现使测试通过 | 失败API测试 | 通过API测试的代码 |
| REFACTOR-API后重构 | API测试通过后重构 | 通过API测试的代码 | 最终重构代码 |
| 测试验证 | 确认测试确实失败/通过 | 测试运行结果 | 验证报告 |

**Memory:**
- 读取: `_bmad/memory/{agent-name}/preferences.md`
- 写入: `_bmad/memory/{agent-name}/daily/{date}.md`

**Init Responsibility:** 理解任务的验收条件和测试范围

**Activation Modes:** Interactive, Headless

**Tool Dependencies:** 测试框架(pytest/jest/etc), 语言对应的测试工具

**Design Notes:**
- 严格遵循两层RED-GREEN-REFACTOR顺序
- 第一层: UT循环，测试单个函数/方法
- 第二层: API测试循环，测试模块间接口契约
- 只有第一层UT通过后才能进入第二层API测试
- 最小化实现，不过度设计

---

### hw-reviewer-{type} (审核Agent基类)

**Type:** Agent (可扩展)

**Persona:** 特定领域的审核专家。从安全、逻辑、性能等特定角度审视代码或文档，发现潜在问题。

**Core Outcome:** 从特定维度提供专业的审核意见，输出结构化的审核报告。

**The Non-Negotiable:** 审核必须客观、有据可依，基于明确的审核标准。

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|------------|---------|--------|---------|
| 安全审核 | 发现安全问题 | 代码/设计文档 | 安全问题报告(P0-P3分级) |
| 逻辑审核 | 发现逻辑问题 | 代码/设计文档 | 逻辑问题报告(P0-P3分级) |
| 性能审核 | 发现性能问题 | 代码/设计文档 | 性能问题报告(P0-P3分级) |
| 风格审核 | 发现风格问题 | 代码 | 风格问题报告(P0-P3分级) |
| 架构审核 | 发现架构问题 | 设计文档 | 架构问题报告(P0-P3分级) |

**Memory:**
- 读取: `_bmad/memory/{agent-name}/preferences.md` (审核标准)
- 写入: `_bmad/memory/hw-shared/reviews/{task-id}-{type}.md`

**Activation Modes:** Interactive, Headless

**Design Notes:**
- 通过skill方式扩展新的审核类型
- 每个审核类型遵循统一的输出格式
- 审核结果写入共享内存供Worktree Controller汇总

---

### hw-knowledge-agent (知识库Agent)

**Type:** Agent

**Persona:** 项目知识的守护者。维护项目知识库，确保知识被有效积累和复用。

**Core Outcome:** 提供知识查询和更新服务，支持设计阶段的知识复用和开发后的知识沉淀。

**The Non-Negotiable:** 知识的准确性和可追溯性。

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|------------|---------|--------|---------|
| 知识查询 | 查询相关已有知识 | 关键词/主题 | 知识条目列表 |
| 知识推荐 | 基于上下文推荐相关知识 | 当前设计/代码 | 推荐知识条目 |
| 知识更新 | 将新知识入库 | 新知识内容 | 更新确认 |
| 知识索引维护 | 维护知识库索引 | - | 索引更新报告 |

**Memory:**
- 读取/写入: `_bmad/memory/hw-shared/knowledge-base/`

**Activation Modes:** Interactive (设计阶段), Headless (开发后自动更新)

**Design Notes:**
- 可选启用
- 设计文档编写时自动查询
- 开发完成后可选刷新知识库

## Configuration

| Variable | Prompt | Default | Result Template | User Setting |
|----------|--------|---------|----------------|-------------|
| `worktree_base` | Worktree目录位置 | `{project-root}/.worktree` | `{project-root}/{value}` | false |
| `min_iteration_before_human` | 人工介入前最小迭代次数 | 3 | - | true |
| `enabled_reviewers` | 启用的审核类型(逗号分隔) | `security,logic,performance` | - | true |
| `knowledge_base_auto_update` | 开发完成后自动更新知识库 | `true` | - | true |
| `merge_strategy` | Worktree合并策略 | `merge` | - | true |

## External Dependencies

| 依赖 | 用途 | 需要的技能 |
|------|------|-----------|
| git | Worktree管理、代码合并 | 内置 |
| pytest/jest/phpunit等 | 单元测试执行 | 按语言选择 |
| 代码风格工具 | 门禁检查(ESLint/Prettier/PHPStan等) | 按语言配置 |
| 安全扫描工具 | 安全门禁(Sonarqube/Snyk等) | 可选 |
| 测试框架 | 集成测试 | 按项目选择 |

## UI and Visualization

**当前版本**: 无UI，纯命令行交互

**未来可能的增强**:
- 进度仪表板: 显示所有worktree的执行状态
- 门禁状态可视化: P0/P1/P2问题汇总
- 知识库浏览: 查看/搜索项目知识库

## Setup Extensions

1. **初始化Worktree目录**: 创建`.worktree/`目录并加入gitignore
2. **初始化共享内存**: 创建`_bmad/memory/hw-shared/`结构
3. **初始化Controller状态**: 创建`_bmad/memory/hw-controller/`结构
4. **配置审核Agent**: 根据`enabled_reviewers`配置启用对应的审核skill

## Integration

**独立使用**: 黑灯工厂可独立运行，完成完整的研发流程

**与其他BMad模块配合**:
- `brainstorming`: 头脑风暴阶段可复用通用 brainstorming skill
- `bmad-agent-builder`: 构建新的审核Agent类型
- `bmad-workflow-builder`: 构建工作流自动化

**扩展点**:
- 通过skill方式添加新的审核类型
- 通过配置启用/禁用功能模块
- 支持对接外部CI/CD系统(预留接口)

## Creative Use Cases

1. **紧急修复场景**: 拆分为hotfix任务，多worktree并行修复
2. **渐进式重构**: 低优先级重构作为后台任务，与主任务并行
3. **A/B功能实验**: 同一功能的多种实现方案并行开发，最终选择最优
4. **知识积累加速**: 每次交付自动沉淀知识，加速后续开发

## Ideas Captured

### 核心愿景
- 企业级软件开发全流程覆盖
- 从头脑风暴 → 设计文档 → 测试设计文档
- 多Agent并行进行文档审核
- TDD方式多Agent并行执行
- API测试驱动开发
- 开发环境集成测试
- 门禁检查
- 多Agent并行检视
- 提交入库
- 测试环境集成测试

### 流程阶段
1. ideation - 头脑风暴
2. 设计 - 设计文档生成
3. 测试设计 - 集成测试设计文档
4. 开发 - TDD驱动开发
5. 验证 - 开发环境集成测试
6. 审核 - 多Agent并行检视
7. 门禁 - 质量门禁检查
8. 提交 - 提交入库
9. 最终验证 - 测试环境集成测试

### 多Agent并行模式（已澄清）
- **审核阶段 - 异构并行**：不同种类的Agent从不同角度分析
  - 例如：安全Agent审安全、逻辑Agent审逻辑、风格Agent审风格
- **执行阶段 - 同构并行**：同一类Agent并行执行相同任务
  - 例如：多个测试Agent同时编写不同模块的UT
- **代码审核阶段 - 异构并行**：不同Agent从不同角度分析
  - 与设计审核类似，多视角协同检视

### 质量门禁概念
- 代码质量检查
- 测试覆盖率
- 安全扫描
- 文档完整性

### TDD驱动开发（已澄清）
- 先写UT测试用例
- 后进行代码开发
- 测试先行确保可测试性

### 关键设计原则
- **验收驱动**：所有开发以验收条件为导向
- **异构审视**：审核/检视用不同视角
- **同构执行**：执行/开发用同一标准
- **质量门禁**：多层检查确保交付质量

### 任务并行模型（已澄清）
- 需求被拆分为多个独立任务
- 任务通过 `git worktree` 实现真正的并行开发
- 每个任务拥有独立的worktree，互不干扰
- 最终通过合并/变基完成集成

### 并行执行架构
```
任务1 (worktree-1) ──┐
任务2 (worktree-2) ──┼── 合并 ──> 主分支
任务3 (worktree-3) ──┘
```

### 总控Agent (Controller)
- 拆分需求为任务
- 创建/管理worktree
- 协调并行执行
- 汇总结果
- 决定何时触发人工介入

### 审核Agent扩展机制
- 使用者可自行添加审核Agent类型
- **通过新的skill方式添加**（遵循统一接口规范）
- 内置基础类型：安全、逻辑、性能
- 通过配置启用/禁用特定审核类型

### 冲突解决机制
- **代码检视审核**：一般不出现冲突
- **架构审核冲突**：由人决策
- **解决流程**：Agent报告冲突 → 人类判断 → 决策记录到共享内存

### 人工介入机制
- 用户配置最低迭代次数（默认3次）
- 超过最低次数后动态判断
- 人工介入：审核 + 协助修改
- 人工是最终决策者

### 阶段验收标准
- 每个阶段有明确的验收标准
- **明确的验收标准是自动化的前提**
- 验收通过后才能进入下一阶段

### 内存架构
- **Agent个人Memory**：各自的学习和偏好
- **共享Memory**：任务进度、跨任务依赖、共享上下文
- **Controller状态**：维护全局进度和整体状态

### 参考整合
- **Subagent-Driven Development**: Controller → Subagent → 两阶段审核 → 状态回报
- **Test-Driven Development**: RED-GREEN-REFACTOR铁律
- **Dispatching Parallel Agents**: 按独立问题域分派Agent
- **Using-Git-Worktrees**: 隔离工作空间基础设施

### 质量门禁模型（已澄清）
**检查维度：**
- 代码风格检查
- 安全问题扫描

**问题分级：**
| 级别 | 名称 | 处理方式 |
|------|------|----------|
| P0 | 致命 (Fatal) | 必须修复，否则阻止进入下一阶段 |
| P1 | 严重 (Severe) | 必须修复，否则阻止进入下一阶段 |
| P2 | 一般 (General) | 必须修复，否则阻止进入下一阶段 |
| P3 | 建议 (Suggestion) | 可选，不阻止流程 |

**门禁原则：P0/P1/P2必须修复才能继续**

### 阶段验收标准（已澄清）
- 每个阶段有明确的验收标准
- **只有验收通过后才能进入下一阶段**
- AI无法满足验收标准时：经过多轮迭代后，人工介入确认

### 测试环境（已澄清）
- 对接各系统的**真实环境**
- 使用**测试数据**
- 非mock环境，保证真实性

### 头脑风暴阶段（已澄清）
- 人 + AI 交互协作，澄清和明确需求
- 澄清完成后 → 多Agent异构并行审查

### 完整流程模型（修正）
```
需求输入
    ↓
[阶段1] 头脑风暴 ← 人+AI交互澄清需求
    ↓ 验收通过
[阶段2] 设计文档编写
    ↓ 验收通过
[阶段3] 基于设计文档 → 任务拆分 → N个任务
    ↓
[阶段4] 多worktree并行执行
    │
    ├─────────────────────────────────────────────────────────────┤
    │                  TDD 两层循环                               │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  【第一层: UT 循环】                                        │
    │     RED ──► 写失败UT ──► 运行确认失败                       │
    │        │                                                     │
    │        ▼                                                     │
    │     GREEN ──► 最小代码通过UT                                 │
    │        │                                                     │
    │        ▼                                                     │
    │     REFACTOR ──► UT通过后重构                               │
    │                                                              │
    │  【第二层: API TEST 循环】                                   │
    │     RED ──► 写失败API测试 ──► 运行确认失败                   │
    │        │                                                     │
    │        ▼                                                     │
    │     GREEN ──► 修复API实现通过API测试                         │
    │        │                                                     │
    │        ▼                                                     │
    │     REFACTOR ──► API测试通过后重构                          │
    │                                                              │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  代码多Agent异构审核                                          │
    │                                                              │
    │  质量门禁检查（P0/P1/P2必须修复）                            │
    │                                                              │
    │  提交到worktree                                              │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘
    ↓
[阶段5] 合并到主分支
    ↓
[阶段6] 测试环境集成测试（真实环境+测试数据）
    ↓ 验收通过
交付
```

### 关键变更说明
- **worktree在任务执行阶段才创建**，不是一开始就创建
- 设计文档是任务拆分的依据
- 头脑风暴和设计文档是前置阶段，在主上下文完成
- 并行worktree执行是核心开发阶段

### 知识库集成（新增）
- **设计阶段**：可参考已有知识库内容
  - 设计文档编写时查询现有知识库
  - 避免重复设计，保持一致性
- **开发完成后**：可选刷新项目知识库
  - 代码开发完成 + 测试通过后
  - 更新项目的知识沉淀
  - 记录设计决策、架构模式、经验教训等

### 关键机制
- **验收驱动**：每阶段有明确验收标准
- **质量门禁**：P0/P1/P2问题必须修复
- **人工兜底**：AI多次迭代无法达标时人工介入
- **真实环境**：测试环境对接真实系统

## Build Roadmap

### 推荐构建顺序

| 顺序 | 技能 | 理由 |
|------|------|------|
| 1 | **hw-controller** | 核心协调者，其他技能依赖它 |
| 2 | **hw-worktree-controller** | 依赖hw-controller提供任务上下文 |
| 3 | **hw-tdd-agent** | 核心执行单元 |
| 4 | **hw-reviewer-security** | 基础审核类型 |
| 5 | **hw-reviewer-logic** | 基础审核类型 |
| 6 | **hw-reviewer-performance** | 基础审核类型 |
| 7 | **hw-knowledge-agent** | 知识库功能（可选后置） |
| 8 | **hw-setup** | 模块安装skill |

### 构建说明

**第一批 (核心)**:
- hw-controller: 最复杂，先构建便于其他技能调试
- hw-worktree-controller: 依赖controller的状态定义
- hw-tdd-agent: 核心TDD执行

**第二批 (审核)**:
- 审核agents可并行构建
- 每个审核类型独立，按需添加新类型

**第三批 (辅助)**:
- hw-knowledge-agent: 可选，知识库功能
- hw-setup: 完整安装体验

### 下一步行动

**Next steps:**

1. Build each skill using **Build an Agent (BA)** or **Build a Workflow (BW)** — share this plan document as context
2. When all skills are built, return to **Create Module (CM)** to scaffold the module infrastructure

---

**Your plan is complete at `skills/reports/2026-04-11-module-plan-ideation.md`. The build roadmap suggests starting with **hw-controller** — shall I invoke **Build an Agent (BA)** now to start building it? I'll pass the plan document as context so the builder understands the bigger picture.**

When all skills are built, return to **Create Module (CM)** to scaffold the module infrastructure.
