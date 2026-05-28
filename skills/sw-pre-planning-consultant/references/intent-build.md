# Intent Analysis: Build from Scratch (从零构建)

## 核心挑战

Build from Scratch 的最常见失败模式是 **在没有充分信息的情况下开始构建**: AI 基于默认假设选择技术栈、项目结构、设计模式，而不是基于实际约束和既有约定。第二个失败模式是 **过早抽象 (premature abstraction)**: 为一个尚未存在的需求构建"通用框架"。

## Phase 1: 探索先于提问 (Explore Before Asking) — 强制协议

这是 Build from Scratch 意图的**强制性步骤**。在向用户提出任何问题之前，必须先执行探索。

### Step 1.1: 代码库探索 (如果非独立项目)

**委托给 `sw-codebase-explorer`**，具体搜索指令:

```
探索目标:
1. 现有项目的技术栈 (语言、框架、包管理器、构建工具)
2. 项目结构和模块组织约定 (monorepo 结构、命名约定)
3. 现有基础设施 (数据库、消息队列、缓存、CI/CD 配置)
4. 共享库和工具 (已有的 common/utils/shared 模块)
5. Lint/Format/Test 配置 (如果有统一的代码规范)
```

**如果代码库探索发现**:
- Monorepo → 新模块必须遵循 monorepo 约定，问题方向变为"如何适配现有结构"
- 已有同类模块 → 新模块应遵循已有模块的模式，问题方向变为"是否复用模式"
- 空仓库 → 真正从零开始，问题方向变为"技术栈和项目结构选择"

### Step 1.2: 外部研究 (通用)

**委托给 `sw-external-researcher`**，搜索指令基于请求内容:

```
研究目标:
1. 该技术领域的最佳实践和推荐的项目结构
2. 相关的 starter templates 或官方脚手架工具
3. 依赖库的最新稳定版本和兼容性
4. 安全基线 (如果涉及认证/授权/数据处理)
```

### Step 1.3: 整合发现

探索完成后，整理发现:
- **已知约束** (从代码库探索): monorepo 结构、技术栈、编码规范
- **推荐方案** (从外部研究): 最佳实践、推荐工具链、项目结构模式
- **信息缺口** (仍需用户确认): 探索无法回答的问题

## Phase 2: 项目上下文分析

### 上下文维度

| 维度 | 从探索自动获得 | 需用户确认 |
|------|---------------|-----------|
| 编程语言 | ✅ (monorepo 约定 / 团队偏好) | 如独立项目且多选项 |
| 框架 | ✅ (已有框架) | 如需选择新框架 |
| 包管理器 | ✅ (已有 lock 文件) | 如需切换 |
| 项目结构 | ✅ (已有约定) | 如需不同模式 |
| 测试框架 | ✅ (已有配置) | 如需不同框架 |
| Lint/Format | ✅ (已有配置) | 如需调整规则 |
| 数据库 | ✅ (已有基础设施) | 如需新增 |
| 部署方式 | ❌ (需确认) | ✅ (通常需确认) |

### MVP 边界定义

从零构建最关键的约束: **什么是最小可用版本?**

```
MVP 范围应由以下约束定义:
- 核心功能: 用户能用它完成什么? (1-2 个核心场景)
- 用户数量: 最初服务多少用户? (1-10 / 100 / 10000)
- 集成需求: 必须与哪些系统交互?
- 时间约束: 第一个可用版本需要多快?
```

### 技术栈选择框架 (如需选择)

如果用户未指定技术栈且探索未发现约束:

```
推荐技术栈选择的自然优先级:
1. 用户明确偏好 > 
2. 团队现有技术栈 (降低认知负荷) > 
3. 生态成熟度 (社区规模、文档质量、维护活跃度) > 
4. 任务适配度 (针对特定场景的最佳工具)
```

**不推荐**: 为新项目引入与团队现有技术栈完全不同的语言/框架，除非有明确的、无法用现有技术栈解决的约束。

## Phase 3: 应问的问题

仅在探索完成后，针对信息缺口提问 (最多 5 个):

1. **MVP 边界** (必问 — 最高优先级):
   ```
   "这个项目的最小可用版本需要做什么? 具体来说:
   - 用户能完成的 1-2 个核心操作是什么?
   - 什么功能可以明确推迟到 v2?"
   ```

2. **部署环境** (高优先级 — 影响架构):
   ```
   "项目将部署在什么环境?
   - 单机运行? 容器化? Serverless?
   - 是否有已确定的目标平台 (AWS/阿里云/Vercel/自建)?"
   ```

3. **技术栈偏好** (如果探索未发现约束):
   ```
   "技术栈方面: 探索发现团队主要使用 [X 语言/Y 框架]。
   新项目是否沿用此技术栈? 还是有特殊原因需要使用其他技术栈?"
   ```

4. **现有系统集成** (如果适用):
   ```
   "新项目需要与哪些现有系统集成?
   - 认证系统? 数据库? 消息队列?
   - 集成接口是已有 API 还是需要同步开发?"
   ```

5. **质量要求** (影响开发流程):
   ```
   "对代码质量和测试覆盖的要求是什么?
   - 是否可以接受 prototype-quality 的初始版本?
   - 还是从一开始就需要 production-quality?"
   ```

## AI-Slop 防护

### 防护 1: 防止过早抽象

**检测信号**: 请求中要求构建 "通用的"、"可扩展的"、"框架级" 的解决方案
**应对**: 在 Planner Directives 中强制 "Solve the specific case first. Abstraction only after 3+ concrete instances."

```
Detected risk: Premature Abstraction
Counter-directive for planner:
  MUST implement the specific solution for the immediate use case first.
  MUST NOT introduce abstraction layers until at least 3 distinct concrete
  use cases exist that share the same pattern.
  When introducing an abstraction, MUST document the 3+ motivating cases.
```

### 防护 2: 防止过度工程化 (Gold-Plating)

**检测信号**: 请求预支未来需求 (handle 1M users, support 10 languages, multi-region deployment)
**应对**: 在 Planner Directives 中强制 "Build for current scale, design for future scale"

```
Detected risk: Gold-Plating
Counter-directive for planner:
  MUST implement for current expected scale, not hypothetical future scale.
  MAY document architecture notes for future scaling (design-doc appendix).
  MUST NOT implement scaling features (sharding, multi-region, i18n) unless
  they are required for the MVP.
```

### 防护 3: 防止技术栈过度设计

**检测信号**: 请求中同时引入多个新技术/基础设施
**应对**: 限制新引入的技术组件数量

```
Detected risk: Tech Stack Over-Engineering
Counter-directive for planner:
  MUST limit new infrastructure components to what is strictly necessary for MVP.
  SHOULD use SQLite/file-based storage over requiring a database server for prototypes.
  Each new infrastructure dependency MUST have an explicit justification.
```

## Planner Directives for Build from Scratch Intent

### MUST 指令

```
MUST define an explicit MVP boundary — list what is IN SCOPE and OUT OF SCOPE for the initial build.
MUST follow the project structure and conventions discovered by sw-codebase-explorer.
MUST use the existing tech stack unless explicitly authorized otherwise.
MUST generate a README.md with setup instructions as the first file.
MUST NOT introduce new programming languages, frameworks, or infrastructure without explicit justification.
```

### SHOULD 指令

```
SHOULD start with the simplest possible implementation — avoid frameworks when a library suffices, avoid libraries when stdlib suffices.
SHOULD set up CI/CD pipeline configuration as part of the initial scaffold.
SHOULD include a minimal test demonstrating the core functionality (not comprehensive coverage).
SHOULD use official scaffolding tools (create-*, npm init, cargo new, etc.) rather than manual setup when available.
```

### MAY 指令

```
MAY defer authentication/authorization to v2 if not core to the MVP functionality.
MAY use in-memory storage for prototype phases if persistence requirements are not yet defined.
```

## QA / Acceptance Criteria for Build from Scratch

1. **[Script]** 项目可构建/运行:
   ```
   验证命令: <build-command> && <run-command>
   预期: 项目成功构建并启动，无致命错误
   ```

2. **[Test Command]** 核心功能测试:
   ```
   验证命令: <test-command> --filter="smoke"
   预期: 所有 smoke tests 通过，验证核心 MVP 功能可用
   ```

3. **[Static Analysis]** 项目结构合规:
   ```
   验证: 项目结构匹配 sw-codebase-explorer 发现的 monorepo/组织约定
   检查项: 目录命名、配置文件位置、模块组织方式
   ```

4. **[Script]** 项目文档完整性:
   ```
   验证: README.md 包含 setup/run/test 三个命令且全部可执行
   命令: grep -c "## Setup" README.md && grep -c "## Run" README.md
   ```

5. **[CI Check]** Lint/Format 基线:
   ```
   验证: 初始代码无 lint 错误
   命令: <lint-command>
   预期: 0 errors
   ```
