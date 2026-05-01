# 服务发现 (Service Discovery)

## 核心理念

服务信息**不应由人工配置**——它是代码的派生信息，应该从代码中自动学习。`service-registry.yaml` 是生成的产物，不是手写的输入。本文件描述如何从 `services/{id}/` 目录中自动检测和提取服务元数据。

## 前置约束 (Pre-flight)

在服务发现运行之前，必须满足:

- [ ] `services/` 目录存在，包含所有相关服务
- [ ] 每个 `services/{id}/` 是一个独立的 git 仓库（有自己的 `.git/`）
- [ ] 每个服务在 `main`（或配置的 `base_branch`）上
- [ ] 每个服务已拉取最新代码 (`git pull origin main`)
- [ ] 每个服务的开发依赖已安装（构建工具可运行）
- [ ] 每个服务的基线测试 100% PASS（验证环境正确）

## 发现流程 (3 步)

### 第 1 步: 服务清单扫描 (Service Inventory)

扫描 `services/` 目录，对每个子目录（排除隐藏目录和非 git 仓库）:

```bash
# 列出所有服务目录
ls -d services/*/ 2>/dev/null | while read dir; do
  if [ -d "$dir/.git" ]; then
    echo "$(basename $dir)"
  fi
done
```

对每个服务，提取基本信息:

| 信息来源 | 提取内容 | 检测方式 |
|---------|---------|---------|
| `services/{id}/.git/config` | Remote URL, base branch | 读 git config |
| `services/{id}/.git/HEAD` | 当前分支 | 读 HEAD 文件 |
| `git log -1 --format=%H` (在服务目录内) | 最新 commit SHA | git 命令 |
| `git status --porcelain` (在服务目录内) | 是否有未提交更改 | git 命令 |

### 第 2 步: 技术栈检测 (Language & Framework Detection)

按照优先级顺序检测，先匹配到的为准:

| 检测标志 | 判定语言 | 判定框架 | 检测文件 |
|---------|---------|---------|---------|
| `build.gradle` 或 `build.gradle.kts` + `src/main/java/` | Java | Spring Boot (如果 `*Application.java` 存在) 或 Gradle | `build.gradle`, `src/main/java/**/Application.java` |
| `pom.xml` + `src/main/java/` | Java | Spring Boot (如果 `*Application.java` 存在) 或 Maven | `pom.xml` |
| `package.json` + `tsconfig.json` | TypeScript | React (`react` in dependencies) 或 Next.js (`next` in dependencies) 或 Express | `package.json` |
| `package.json` (无 tsconfig) | JavaScript | React / Vue / Angular / Express | `package.json` |
| `requirements.txt` 或 `pyproject.toml` + `*.py` | Python | FastAPI (`fastapi` in deps) 或 Django (`django` in deps) 或 Flask | `requirements.txt`, `pyproject.toml` |
| `go.mod` + `*.go` | Go | Gin (`gin-gonic` in go.mod) 或 Echo 或 标准库 | `go.mod` |
| `Cargo.toml` + `src/main.rs` | Rust | Actix / Axum / Rocket | `Cargo.toml` |

**构建命令推导:**

| 语言/框架 | 构建命令 | 测试命令 | 启动命令 |
|----------|---------|---------|---------|
| Java/Gradle | `./gradlew build -x test` | `./gradlew test` | `./gradlew bootRun` |
| Java/Maven | `mvn install -DskipTests` | `mvn test` | `mvn spring-boot:run` |
| TypeScript/npm | `npm ci` | `npm test` | `npm run dev` |
| Python/pip | `pip install -r requirements.txt` | `pytest` | `python main.py` 或 `uvicorn` |
| Go | `go mod download` | `go test ./...` | `go run main.go` |

### 第 3 步: API 与数据检测 (Endpoint & Schema Detection)

**API 端点检测:**

| 语言/框架 | 检测文件模式 | 提取内容 |
|----------|------------|---------|
| Java/Spring Boot | `src/main/java/**/controller/*Controller.java` 或 `*Resource.java` | `@GetMapping/@PostMapping/@PutMapping/@DeleteMapping` 路径 + `@RequestMapping` 前缀 |
| Java/Spring Boot | `src/main/java/**/controller/*Controller.java` | `@RestController` 注解 → REST API |
| TypeScript/Express | `src/**/*.router.ts` 或 `src/**/*.routes.ts` | `router.get/post/put/delete('/path', ...)` |
| TypeScript/Next.js | `src/app/**/route.ts` 或 `pages/api/**/*.ts` | App Router / Pages Router API 路径 |
| Python/FastAPI | `**/*.py` + `@app.get/@app.post/@app.put/@app.delete` | 装饰器路径 + router |
| Go/Gin | `**/*.go` + `router.GET/POST/PUT/DELETE` | 路由注册路径 |

**提取每个端点的:**
- HTTP Method + Path
- 请求参数 (path/query/body)
- 响应类型 (从返回类型或注解)

**端口检测:**

| 来源 | 检测方式 |
|------|---------|
| Spring Boot | `src/main/resources/application.yml` 或 `.properties` 中 `server.port` |
| Node.js | `package.json` scripts 或 `.env` 中 `PORT` |
| Python | `.env` 或环境变量 `PORT` |
| Go | `main.go` 或 config 中端口常量 |
| Dockerfile | `EXPOSE {port}` |
| docker-compose | `ports: "{host}:{container}"` |

默认端口（无法检测时）: Java=8080, Node=3000, Python=8000, Go=8080

**数据库 Schema 检测:**

| 来源 | 检测方式 |
|------|---------|
| Flyway | `src/main/resources/db/migration/V*__.sql` → 提取 CREATE TABLE / ALTER TABLE |
| Liquibase | `src/main/resources/db/changelog/*.xml` → 提取 changeSet |
| Prisma | `prisma/schema.prisma` → 提取 model 定义 |
| SQLAlchemy | `models/*.py` → 提取 class 定义 + Column |
| GORM | `models/*.go` → 提取 struct + gorm tag |
| TypeORM | `src/**/*.entity.ts` → 提取 @Entity + @Column |

**基础设施依赖检测:**

| 依赖标志 | 判定依赖 | 检测方式 |
|---------|---------|---------|
| `spring-boot-starter-data-jpa` + `postgresql` driver | PostgreSQL | `build.gradle` / `pom.xml` |
| `spring-boot-starter-data-redis` 或 `redis` client | Redis | 同上 |
| `spring-kafka` 或 `kafka-clients` | Kafka | 同上 |
| `spring-cloud-starter-aws` 或 `aws-sdk` | S3 | 同上 |
| `mongoose` 或 `mongodb` driver (Node) | MongoDB | `package.json` |
| `redis` / `ioredis` (Node) | Redis | `package.json` |

**跨服务依赖检测:**

扫描代码中对外部服务 URL 的引用:

```bash
# 在服务目录内搜索可能引用其他服务的 URL 模式
grep -r "http://.*:[0-9]\+" src/ 2>/dev/null
grep -r "api/v[0-9]" src/ 2>/dev/null
grep -r "service.*url\|SERVICE.*URL\|service.*host" src/ 2>/dev/null
```

同时检查配置文件中的服务 URL:

```bash
# Spring Boot
grep -r "url:" src/main/resources/application*.yml 2>/dev/null

# Node.js
grep -r "SERVICE_URL\|API_URL" .env* 2>/dev/null
```

## 输出产物: service-registry.yaml

将检测结果写入 `_bmad/memory/hw-shared/service-registry.yaml`:

```yaml
# Auto-generated by hw-knowledge-agent service-discovery
# DO NOT EDIT MANUALLY — regenerated on each discovery run
generated_at: "{timestamp}"
generated_by: "hw-knowledge-agent"

services:
  - id: "user-service"
    name: "User Service"
    
    # --- Git info ---
    repo_remote: "git@github.com:org/user-service.git"
    base_branch: "main"
    current_branch: "main"
    latest_commit: "abc123def456..."
    has_uncommitted_changes: false
    
    # --- Tech stack (auto-detected) ---
    language: "java"
    framework: "spring-boot"
    build_tool: "gradle"
    java_version: "17"
    build_command: "./gradlew build -x test"
    test_command: "./gradlew test"
    start_command: "./gradlew bootRun"
    
    # --- Runtime ---
    port: 8081
    health_check: "/actuator/health"
    health_check_timeout_ms: 5000
    
    # --- APIs (auto-detected from controllers) ---
    apis:
      - method: "GET"
        path: "/api/v1/users/{id}"
        controller: "UserController"
        returns: "UserResponse"
        auth_required: true
      - method: "POST"
        path: "/api/v1/users"
        controller: "UserController"
        returns: "UserResponse"
        auth_required: false  # registration endpoint
      - method: "PUT"
        path: "/api/v1/users/{id}/preferences"
        controller: "UserPreferencesController"
        returns: "UserPreferencesResponse"
        auth_required: true
    
    # --- Data (auto-detected from migrations) ---
    owns_data:
      - table: "users"
        migration: "V001__create_users.sql"
        primary_key: "id UUID"
        columns: ["username", "email", "password_hash", "role", "status", "created_at", "updated_at"]
        sensitive_columns: ["password_hash", "email"]
      - table: "user_preferences"
        migration: "V005__create_user_preferences.sql"
        primary_key: "user_id UUID (FK → users)"
        columns: ["user_id", "theme", "language", "notification_email", "notification_push"]
    
    # --- Infrastructure dependencies (auto-detected) ---
    depends_on_infra:
      - type: "postgres"
        version: "16"
        database: "userdb"
      - type: "redis"
        version: "7"
        usage: "session_cache"
      - type: "kafka"
        topics_produced: ["UserCreated", "UserPreferencesUpdated"]
        topics_consumed: []
    
    # --- Cross-service dependencies (auto-detected from URLs in config/code) ---
    depends_on_services: []  # user-service is a leaf — no dependencies
    depended_by_services: []  # filled after scanning all services
    
    # --- Knowledge base ---
    knowledge_path: "knowledge-base/services/user-service/"

# --- Dependency graph (computed after scanning all services) ---
dependency_graph:
  user-service:
    depends_on: []
    depended_by: ["order-service", "notification-service"]
  order-service:
    depends_on: ["user-service"]
    depended_by: ["web-frontend"]
  web-frontend:
    depends_on: ["bff-service"]
    depended_by: []
```

## 服务知识文件自动生成

除了 `service-registry.yaml`，发现过程还为每个服务生成知识文件:

### services/{id}/overview.md

```markdown
# {服务名称} ({service-id})

**语言:** {language} {version}
**框架:** {framework}
**端口:** {port}
**健康检查:** {health_check}
**Repo:** {repo_remote}

## 职责

{从 README.md 或 package.json description 提取，或标记为 NEEDS_MANUAL}

## API 端点 (共 {n} 个)

| Method | Path | Auth | Controller |
|--------|------|------|-----------|
| GET | /api/v1/users/{id} | 需要 | UserController |
| POST | /api/v1/users | 不需要 | UserController |
| ... | ... | ... | ... |

## 数据库 (共 {n} 张表)

| 表名 | 主键 | 敏感列 |
|------|------|--------|
| users | id UUID | email, password_hash |
| user_preferences | user_id UUID (FK) | — |

## 基础设施依赖

- PostgreSQL 16 (userdb)
- Redis 7 (session_cache)
- Kafka → produces: UserCreated, UserPreferencesUpdated

## 依赖的服务

- {空 或 列表}

## 被依赖的服务

- {空 或 列表}

## 最近变更

{git log --oneline -5}
```

### services/{id}/api-endpoints.md

每个端点的详细文档（从 controller/route 文件的注释和注解中提取）。

### services/{id}/db-schema.md

数据库表结构（从 migration 文件中提取 DDL，格式化为 markdown 表格）。

## 与服务注册表的同步

- **初始生成:** hw-setup 在服务 bootstrap 时调用服务发现
- **增量更新:** 每个 worktree 任务完成后，如果修改了 controller / migration / config → 重新扫描该服务的对应部分
- **定期全量:** 每个需求完成后，全量重新发现一次（耗时但准确）
- **手动触发:** 通过 `hw-knowledge-agent` 的 "重新发现服务" 能力

## 检测失败处理

| 失败场景 | 降级策略 |
|---------|---------|
| 语言/框架无法识别 | 标记为 `unknown`，提示人工标注 |
| 端口无法检测 | 使用默认端口 (Java=8080, Node=3000)，提示人工确认 |
| API 端点检测不完整 | 标记为 `PARTIAL`，记录检测到的数量和置信度 |
| DB Schema 检测不到 migration 文件 | 标记为 `NO_MIGRATIONS_FOUND`，检查是否有其他 schema 管理方式 |
| 跨服务依赖无法确定 | 标记为 `NEEDS_ANALYSIS`，在交叉分析阶段由人工补充 |
