# 微服务架构适配 (Microservice Architecture Adaptation)

此文件是**架构适配层**——当 `_bmad/config.yaml` 中 `architecture: "microservices"` 时自动加载。它在现有单体流程上叠加微服务逻辑，不改动通用模板的核心结构，而是注入扩展规则。

## 概述

微服务架构下，一个需求不再是"一个 repo 里的一个功能"，而是"跨越多个服务的一次业务能力变更"。每个阶段的工作方式发生根本变化:

```
单体:     1 repo × N worktrees → 1 merge → 1 deploy
微服务:   N repos × M worktrees (per service) → 独立 merge (per service) → 协调 deploy
```

## 设计决策: 服务 Co-location

**所有服务必须放在同一个项目根目录下（monorepo-style co-location），不引入服务级 Agent。**

### 目录结构

```
{project-root}/
├── services/                        # 所有服务 co-locate 在此
│   ├── user-service/                # git clone git@...org/user-service.git
│   │   ├── src/
│   │   ├── build.gradle
│   │   └── .git/                    # 独立 git 仓库
│   ├── order-service/               # git clone git@...org/order-service.git
│   └── web-frontend/                # git clone git@...org/web-frontend.git
├── _bmad/memory/                    # 统一共享状态 (不变)
│   └── hw-shared/
├── .worktree/                       # 所有 worktree 在此 (按服务分目录)
│   ├── user-service/
│   │   ├── hw-task-001/
│   │   └── hw-task-002/
│   ├── order-service/
│   │   └── hw-task-003/
│   └── web-frontend/
│       └── hw-task-004/
└── contracts/                       # 跨服务 API 契约 (共享)
    ├── user-service-openapi.yaml
    └── order-service-openapi.yaml
```

### 为什么 co-locate

| 维度 | co-locate (推荐) | 分散目录 (复杂) |
|------|-----------------|---------------|
| Agent 拓扑 | hw-controller → worktree-controller × N (不变) | 需要 hw-service-context 协调层 |
| 共享状态 | `_bmad/memory/` 天然共享 | 需要分布式状态或远程存储 |
| Worktree 路径 | `.worktree/{service}/hw-task-{id}` (多一层前缀) | 跨文件系统，git worktree 不支持 |
| 契约文件 | `contracts/` 一目录共享 | 需要显式同步或远程 fetch |
| 成本追踪 | 一处汇总 | 跨进程/跨机器聚合 |
| Git 独立性 | 每个 `services/{id}/` 是独立 git 仓库，独立 remote、独立历史 | 同左 |
| CI/CD 独立性 | 每个服务独立 CI，与 co-locate 不冲突 | 同左 |

### 关于 git 独立性

Co-location 不影响服务的 git 独立性。`services/user-service` 和 `services/order-service` 是不同的 git 仓库，有不同的 remote、不同的提交历史、不同的分支策略。它们只是在同一个父目录下——就像一个 IDE 里同时打开多个项目。

```bash
# 初始化: 克隆服务到 services/ 下
cd {project-root}
git clone git@github.com:org/user-service.git services/user-service
git clone git@github.com:org/order-service.git services/order-service
git clone git@github.com:org/web-frontend.git services/web-frontend

# 每个服务独立操作
cd services/user-service && git log --oneline    # user-service 的历史
cd services/order-service && git log --oneline   # order-service 的历史, 完全独立
```

### 何时考虑服务级 Agent

以下场景在 v1 中不会出现，标记为未来扩展点:
- 服务分布在不同的机器/集群上（→ 需要分布式编排，超出文件系统范围）
- 单个服务需要独立的 budget/cost 追踪（→ 需要服务级成本会计）
- 不同服务有不同的 hw-controller 配置策略（→ 需要配置隔离）

这些场景出现时，方案不是加 `hw-service-context` 协调层，而是在每个服务目录下跑独立的 hw-controller 实例 + controller-to-controller 通信协议。

## 配置

```yaml
# _bmad/config.yaml
hw:
  architecture: "microservices"    # "monolith" (默认) | "microservices"
  
  # 微服务专属配置
  microservices:
    service_registry: "_bmad/memory/hw-shared/service-registry.yaml"
    contract_testing: true          # 是否启用跨服务契约测试
    integration_test_mode: "docker-compose"  # "docker-compose" | "k8s" | "manual"
    max_parallel_services: 4        # 最多同时开发的服务数
    contract_first: true            # 是否要求契约先行（推荐 true）
```

## 新增全局状态

### 服务注册表 (Service Registry)

```yaml
# _bmad/memory/hw-shared/service-registry.yaml
architecture: "microservices"
created_at: "{timestamp}"

services:
  - id: "{service-id}"               # kebab-case, 如 user-service
    name: "{服务名称}"
    repo: "git@github.com:{org}/{service-id}.git"   # git remote (clone 目标)
    local_path: "services/{service-id}"              # 相对于 project-root
    base_branch: "main"
    language: "java-springboot|typescript-react|python-fastapi|go-gin|..."
    port: {port_number}
    health_check: "/actuator/health|/api/health|/"
    
    owns_data:
      - table: "{table_name}"
        schema: "{schema_path}"
      - topic: "{kafka_topic}"
        schema: "{avro_path}"
    
    provides_apis:
      - path: "/api/v1/{resource}"
        spec: "contracts/{service-id}-openapi.yaml"
        consumers: ["{consumer_service_id}"]
    
    consumes_apis:
      - provider: "{provider_service_id}"
        path: "/api/v1/{resource}"
        spec: "contracts/{provider_service_id}-openapi.yaml"
    
    depends_on_infra:
      - type: "postgres|redis|kafka|s3"
        instance: "{instance_name}"
        migration_path: "src/main/resources/db/migration/"

  - id: "{another-service-id}"
    ...

dependency_graph:
  # 服务间依赖（单向，不允许循环）
  "{service-id}":
    depends_on: ["{dependency_service_id}"]
    depended_by: ["{consumer_service_id}"]
```

### 服务依赖图规则

- **禁止循环依赖。** 如果 A → B 且 B → A → 架构问题，升级人工
- **运行时依赖** (B 的 API 被 A 调用) 和**构建时依赖** (A 的代码 import B 的 SDK) 要区分
- **契约文件** 是服务间唯一的事实源——服务 A 不直接读服务 B 的代码

## 各阶段适配

### 需求阶段 (Ideation)

**与单体差异:** 需求分析时需要识别影响哪些服务。

**需求模板额外章节 (microservices 模式下自动追加):**

#### 服务影响分析 (Service Impact Analysis)

| 服务 | 影响类型 | 变更内容 | 依赖服务 | 风险等级 |
|------|---------|---------|---------|---------|
| `user-service` | 修改 API | 新增 `GET /api/v1/users/{id}/preferences` | — | 低 |
| `order-service` | 新增 consumer | 调用 user-service 新 API 校验用户状态 | `user-service` | 中 |
| `web-frontend` | 新增页面 | 用户偏好设置页面 → 调用 BFF → user-service | `bff-service` | 低 |
| `notification-service` | 新增事件订阅 | 监听 `UserPreferencesUpdated` 事件 | — | 低 |

**服务影响规则:**
- 标注每个服务的变更类型: 新增 API / 修改 API / 新增 consumer / 新增事件 / 数据迁移
- 跨服务依赖必须显式标注——不能假设"自然就知道"

**需求澄清额外问题 (microservices 模式下追加):**
- "这个需求涉及哪些服务？各服务改什么？"
- "有没有需要跨服务协调的数据一致性场景？"
- "是否需要新增服务间 API 调用？契约谁来定义？"

### 设计阶段 (Design)

**与单体差异:** 设计文档增加服务交互图和跨服务契约设计。

**设计模板额外章节:**

#### 服务交互设计 (Service Interaction Design)
(追加到 design-doc-template.md Section 5 架构设计之后)

```
# 服务交互序列

用户 → web-frontend → bff-service → user-service → DB
                         │
                         └──→ order-service → DB
                                  │
                                  └──→ notification-service → Kafka → email-service
```

| 步骤 | 调用方 | 被调用方 | 协议 | 路径/事件 | 同步/异步 | SLA | 降级策略 |
|------|--------|---------|------|----------|----------|-----|---------|
| 1 | web-frontend | bff-service | HTTP | POST /api/v1/preferences | 同步 | < 200ms | 显示缓存值 |
| 2 | bff-service | user-service | HTTP | PUT /api/v1/users/{id}/preferences | 同步 | < 100ms | 返回 503 + 重试提示 |
| 3 | user-service | kafka | Event | `UserPreferencesUpdated` | 异步 | < 1s | 死信队列重试 |
| 4 | notification-service | kafka | Event | `UserPreferencesUpdated` | 异步 | — | — |

#### 跨服务契约设计 (Cross-Service Contract)
(追加到 design-doc-template.md Section 6 API/接口设计之后)

如果需求涉及新增或修改服务间 API 调用，每个跨服务 API 端点需要契约定义:

```yaml
# contracts/user-service-openapi.yaml (片段)
paths:
  /api/v1/users/{id}/preferences:
    put:
      operationId: updateUserPreferences
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [theme, language, notifications]
              properties:
                theme:
                  type: string
                  enum: [light, dark, auto]
                language:
                  type: string
                  pattern: '^[a-z]{2}(-[A-Z]{2})?$'
                notifications:
                  type: object
                  properties:
                    email:
                      type: boolean
                    push:
                      type: boolean
      responses:
        '200':
          description: 更新成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserPreferences'
        '404':
          $ref: '#/components/schemas/NotFoundError'
```

**契约管理规则:**
- 契约文件路径: `contracts/{service-id}-openapi.yaml`
- 契约文件由**提供方**维护，**消费方**审查
- 契约变更必须兼容（additive change）或版本升级（breaking change）
- `contract_first: true` 时，契约必须先于实现代码存在

### 任务拆分 (Task Decomposition)

**与单体差异:** 任务按服务分组，每个任务绑定到具体服务。

**追加到 task-decomposition.md 的拆分规则:**

#### 微服务任务分组

```yaml
# tasks.yaml (微服务模式)
requirement_id: "{REQ-YYYYMMDD-NNN}"
architecture: "microservices"

service_groups:
  - service_id: "user-service"
    repo: "git@github.com:org/user-service.git"
    tasks:
      - task_id: "hw-001"
        name: "user-service: 新增 UserPreferences API"
        component: "UserPreferencesController"
        ...
        cross_service_dependencies: []  # 本服务内部依赖
        
  - service_id: "order-service"
    repo: "git@github.com:org/order-service.git"
    tasks:
      - task_id: "hw-002"
        name: "order-service: 调用 user-service 校验用户状态"
        component: "UserStateValidator"
        ...
        cross_service_dependencies:
          - task_id: "hw-001"
            contract: "contracts/user-service-openapi.yaml"
            type: "CONTRACT"  # 依赖的是契约，不是代码

  - service_id: "web-frontend"
    repo: "git@github.com:org/web-frontend.git"
    tasks:
      - task_id: "hw-003"
        name: "web-frontend: 用户偏好设置页面"
        component: "UserPreferencesPage"
        ...
        cross_service_dependencies:
          - task_id: "hw-001"  # 需要 API 契约就绪
            contract: "contracts/user-service-openapi.yaml"
            type: "CONTRACT"
```

#### 跨服务依赖类型 (追加到 task-decomposition.md 第 2 步)

| 类型 | 含义 | 微服务下的行为 |
|------|------|-------------|
| **CONTRACT** | 依赖提供方服务的 API 契约 | 提供方先定义契约（不一定要实现）→ 消费方基于契约开发 mock → 双方并行 |
| **API_READY** | 依赖提供方服务的 API 真实可用 | 提供方先实现 + 部署到集成环境 → 消费方联调 — 降低并行度 |
| **EVENT** | 依赖事件 schema | 提供方先定义事件 schema（Avro/Protobuf/JSON Schema）→ 双方并行开发 |
| **DATA_MIGRATION** | 依赖数据迁移完成 | 上游服务的 DB migration 先执行 → 下游才能读写 |

**并行度对比:**

| 依赖类型 | 单体 | 微服务 |
|---------|------|--------|
| CODE 依赖 | 串行（同一 repo） | N/A（服务间不能有代码依赖） |
| CONTRACT 依赖 | N/A | 可并行（契约先行 + mock） |
| API_READY 依赖 | N/A | 串行（或部分并行 + mock） |
| 无依赖 | 并行 | 并行（不同 repo 天然并行） |

### Worktree 管理 (Worktree Management)

**与单体差异:** 不再是一个 project root 下的 worktree，而是每个服务 repo 各自创建 worktree。

**追加到 worktree-management.md:**

#### 多仓库 Worktree 创建

```bash
# 微服务模式: 为每个服务在 services/{service-id} 下创建 worktree
# 所有 worktree 统一在 {project-root}/.worktree/{service-id}/ 下

# 服务: user-service (repo root = services/user-service)
cd {project-root}/services/user-service
git worktree add ../../.worktree/user-service/hw-task-001 -b hw-task-001 main

# 服务: order-service (repo root = services/order-service)  
cd {project-root}/services/order-service
git worktree add ../../.worktree/order-service/hw-task-003 -b hw-task-003 main

# 服务: web-frontend (repo root = services/web-frontend)
cd {project-root}/services/web-frontend
git worktree add ../../.worktree/web-frontend/hw-task-004 -b hw-task-004 main
```

**路径规则:**
- 服务 repo root: `{project-root}/services/{service-id}/`
- Worktree 路径: `{project-root}/.worktree/{service-id}/hw-task-{id}/`
- Worktree 创建命令在服务 repo root 下执行，worktree 路径用相对路径指回 `.worktree/`

#### 服务级 Worktree 注册表

```yaml
# worktree-registry.yaml (微服务模式)
architecture: "microservices"

services:
  user-service:
    repo_root: "services/user-service"          # 相对于 project-root
    worktree_base: ".worktree/user-service"      # 相对于 project-root
    base_branch: "main"
    language: "java-springboot"
    port: 8081
    worktrees:
      hw-task-001:
        branch: "hw-task-001"
        task_id: "hw-001"
        path: ".worktree/user-service/hw-task-001"
        status: "running"
        
  order-service:
    repo_root: "services/order-service"
    worktree_base: ".worktree/order-service"
    base_branch: "main"
    language: "java-springboot"
    port: 8082
    worktrees:
      hw-task-003:
        branch: "hw-task-003"
        task_id: "hw-003"
        path: ".worktree/order-service/hw-task-003"
        status: "pending"
```

#### 服务独立环境搭建

每个服务的 worktree 执行该服务自己的环境搭建命令（可能不同语言/框架）:

| 服务 | 语言 | 搭建命令 | 基线验证命令 |
|------|------|---------|------------|
| user-service | Java/Spring Boot | `./gradlew build -x test` | `./gradlew test` |
| web-frontend | TypeScript/React | `npm ci` | `npm test` |
| order-service | Java/Spring Boot | `./gradlew build -x test` | `./gradlew test` |

### 并行执行 (Parallel Execution)

**与单体差异:** 不同服务的任务天然并行，但需要契约协调。

**追加到 parallel-execution.md:**

#### 跨服务协调策略

```
Wave 1: 所有无依赖的任务（跨服务同时启动）
  ├── hw-001 (user-service)     ← 提供方: 定义契约 + 实现
  ├── hw-004 (notification-svc) ← 独立服务
  └── hw-005 (infra-setup)      ← 基础设施

Wave 2: 依赖 Wave 1 的 CONTRACT 型任务（基于契约并行）
  ├── hw-002 (order-service)    ← 消费方: 基于 user-service 契约做 mock 开发
  └── hw-003 (web-frontend)     ← 消费方: 基于 user-service 契约做 mock 开发

Wave 3: 需要 API_READY 的任务（集成环境联调）
  ├── 部署 user-service 到集成环境
  ├── hw-002 切换到真实 API（替换 mock）
  └── hw-003 切换到真实 API（替换 mock）

Wave 4: E2E 和跨服务集成测试
  ├── 所有服务部署到集成环境
  ├── 契约测试
  └── E2E 测试
```

#### 服务间协调通信

当任务 B 依赖任务 A 的 CONTRACT 时:
1. 任务 A 完成契约定义 → 写入 `contracts/{service-id}-openapi.yaml`
2. 总控通知任务 B: "契约已就绪，路径为 {contract_path}"
3. 任务 B 读取契约 → 生成 mock server → 开始并行开发
4. 任务 A 完成 API 实现 → 总控通知任务 B: "API 已就绪，可切换真实调用"
5. 任务 B 替换 mock 为真实调用 → 验证通过

### 质量门禁 (Quality Gates)

**与单体差异:** 增加契约测试层，E2E 需要多服务编排。

**质量门禁层级变化:**

```
单体:
  UT → API → E2E

微服务:
  UT (per service) → API (per service) → Contract (跨服务) → Integration (全系统) → E2E (全系统)
```

**追加到 quality-gates.md:**

#### GATE 1.5: 契约测试 (Contract Testing)

在 API 测试通过后、E2E 测试前:

```bash
# 对每个跨服务 API 依赖，消费方运行契约测试
# 使用 Postman/Newman 验证提供方 API 是否符合契约

# 示例: order-service 验证 user-service 的 API 契约
newman run contracts/user-service-contract-tests.json \
  -e contracts/user-service-env.json \
  --reporters cli,junit
```

**契约测试验证维度:**

| 验证项 | 方法 | 阻塞? |
|--------|------|--------|
| 端点存在 | 调用契约中定义的所有端点 | P0 |
| 请求/响应 schema 匹配 | JSON Schema 校验 | P0 |
| 状态码正确 | 正常+异常场景的预期状态码 | P0 |
| 响应时间在 SLA 内 | 测量 p95 延迟 | P1 |
| 向后兼容 | 旧版本客户端仍可正常调用 | P0 (major version) |

#### GATE 3: 集成测试 (Integration Test — 多服务编排)

**集成环境启动 (docker-compose 模式):**

```yaml
# docker-compose.integration.yaml
version: '3.8'
services:
  user-service:
    build:
      context: ./services/user-service
      dockerfile: Dockerfile
    ports:
      - "8081:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=integration
    depends_on:
      - postgres
      
  order-service:
    build:
      context: ./services/order-service
      dockerfile: Dockerfile
    ports:
      - "8082:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=integration
      - USER_SERVICE_URL=http://user-service:8080
    depends_on:
      - postgres
      - user-service  # 健康检查通过后才启动
      
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: integration_test
    ports:
      - "5432:5432"
```

**集成测试执行:**

```bash
# 1. 启动集成环境
docker-compose -f docker-compose.integration.yaml up -d

# 2. 等待所有服务健康检查通过
for service in user-service order-service; do
  until curl -s http://localhost:${PORT}/actuator/health | grep UP; do
    sleep 5
  done
done

# 3. 运行跨服务集成测试
# 3a. 契约测试
newman run contracts/user-service-contract-tests.json \
  -e contracts/user-service-env.json

# 3b. 跨服务场景测试 (Postman Collection)
newman run tests/integration-cross-service.json \
  -e tests/integration-env.json

# 4. E2E 测试 (含 UI)
npx playwright test e2e/

# 5. 清理
docker-compose -f docker-compose.integration.yaml down -v
```

#### 跨服务回归检测

如果一个服务的变更导致另一个服务的测试失败:

```
1. 集成测试报 FAIL
2. git bisect 定位到服务 A 的某次 merge
3. 检查服务 A 的变更是否违反契约:
   - 修改了 API 响应 schema？→ 必须更新契约
   - 修改了 API 行为？→ 消费方需要适配
   - 修改了数据库 schema？→ 消费方的数据迁移是否兼容
4. 如果违反契约 → 回滚服务 A 的变更
5. 如果是消费方的假设过于脆弱 → 修复消费方的测试
```

### 交付阶段 (Delivery)

**与单体差异:** 多服务协调发布，版本管理。

**追加到 delivery-checklist.md 和 release-notes-template.md:**

#### 多服务发布协调

```yaml
# _bmad/memory/hw-shared/delivery/release-plan-{id}.yaml
requirement_id: "{REQ-YYYYMMDD-NNN}"
release_version: "v1.3.0"
release_date: "{timestamp}"

release_sequence:
  - wave: 1  # 数据迁移 + 基础设施
    services:
      - id: "user-service"
        version: "v1.3.0"
        type: "db_migration"  # 向后兼容迁移，先执行
        rollback: "flyway undo"
        
  - wave: 2  # 提供方服务先上线
    services:
      - id: "user-service"
        version: "v1.3.0"
        type: "api_deploy"
        depends_on: ["wave-1"]
        health_check: "GET /actuator/health"
        rollback: "rollback to v1.2.5"
        
  - wave: 3  # 消费方服务后上线
    services:
      - id: "order-service"
        version: "v2.0.1"
        type: "api_deploy"
        depends_on: ["wave-2"]
        rollback: "rollback to v2.0.0"
      - id: "web-frontend"
        version: "v1.5.0"
        type: "static_deploy"
        depends_on: ["wave-2"]
        rollback: "revert to v1.4.9 CDN cache"

rollback_plan:
  trigger: "任一服务健康检查连续失败 3 次 OR P0 告警触发"
  steps:
    - 停止 wave 3 部署
    - 逐个回滚 wave 3 服务
    - 如果问题持续 → 回滚 wave 2 服务
    - 数据迁移不回滚（向后兼容），除非数据损坏
```

#### 契约版本管理

```
契约文件命名规范:
  contracts/{service-id}-openapi.yaml     ← 当前最新版本 (开发中的)
  contracts/{service-id}-openapi-v1.yaml  ← 已发布版本 (不可变)
  contracts/{service-id}-openapi-v2.yaml  ← 下一个大版本的 WIP

版本策略:
  - 新增可选字段 → 小版本，不破坏兼容性
  - 新增必填字段 / 删除字段 / 修改字段类型 → 大版本，创建新契约文件
  - 旧版本契约支持至少 2 个大版本的过渡期
```

## 与单体模式的切换

### 检测方式

```yaml
# _bmad/config.yaml
hw:
  architecture: "microservices"  # 或 "monolith" (默认)
```

### 加载逻辑

在 SKILL.md On Activation 中:

```
1. Read config.yaml → hw.architecture
2. If "microservices" → Load references/microservice-adaptation.md
3. If "monolith" → Skip (use base templates)
4. All existing templates still load — adaptation layer injects extra sections/rules
```

### 适配层注入点

| 阶段 | 注入方式 | 注入内容 |
|------|---------|---------|
| 需求 | 追加到 requirements-spec-template | 服务影响分析表 |
| 需求 | 追加到 requirement-clarification | 跨服务依赖提问 |
| 设计 | 追加到 design-doc-template | 服务交互设计 + 跨服务契约 |
| 拆分 | 覆盖 task-decomposition | 按服务分组 + CONTRACT 依赖类型 |
| 执行 | 覆盖 worktree-management | 多 repo worktree 创建 |
| 执行 | 追加到 parallel-execution | 跨服务 wave 协调 |
| 执行 | 追加到 quality-gates | 契约测试层 + 集成测试编排 |
| 交付 | 追加到 delivery-checklist | 多服务发布序列 + 契约版本管理 |

## 输出产物 (微服务追加)

| 产物 | 路径 | 用途 |
|------|------|------|
| 服务注册表 | `_bmad/memory/hw-shared/service-registry.yaml` | 服务列表 + 依赖图 |
| 跨服务契约 | `contracts/{service-id}-openapi.yaml` | 服务间 API 契约 |
| 契约测试 | `contracts/{service-id}-contract-tests.json` | Postman Collection for contract testing |
| 集成编排 | `docker-compose.integration.yaml` | 集成测试环境编排 |
| 发布计划 | `delivery/release-plan-{id}.yaml` | 多服务发布序列 + 回滚 |
