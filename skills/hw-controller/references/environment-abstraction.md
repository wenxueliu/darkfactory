# 环境抽象层 (Environment Abstraction Layer)

## 核心理念

不同产品/团队使用不同的部署技术 —— Docker Compose、Kubernetes、裸金属本地进程。它们有不同环境层级 —— 开发、测试、预发布、生产。**框架不能绑定任何一种具体技术**，否则换个产品就跑不动。

环境抽象层定义了框架需要的**统一接口**，每个产品通过配置选择对应的**Provider 实现**。框架代码只操作抽象接口，不感知底层技术。

## 环境层级 (Environment Tiers)

框架定义了 4 个标准环境层级。每个层级有明确的用途和 Provider 要求:

```
┌─────────────────────────────────────────────────────────────────┐
│                      环境层级与测试映射                           │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  worktree-   │ integration  │   staging     │   production      │
│  local       │              │              │                   │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ 第一轮 API   │ 第三轮 API   │ 预发布门禁    │ 生产监控          │
│ 单服务本地   │ + E2E        │ 灰度/金丝雀   │ 只读 (不测试)     │
│ 不需要集成   │ 所有服务部署  │ 生产镜像      │                   │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ Provider:    │ Provider:    │ Provider:    │ Provider:         │
│ local-proc   │ docker, k8s, │ k8s,         │ k8s, ...          │
│              │ local-proc   │ docker, ...  │                   │
└──────────────┴──────────────┴──────────────┴───────────────────┘
```

| 层级 | 用途 | 测试阶段 | 服务范围 | 生命周期 |
|------|------|---------|---------|---------|
| `worktree-local` | 任务内 TDD 开发 | GATE 1: UT + API (单服务) | 1 个服务 | 随 worktree 创建/销毁 |
| `integration` | 跨服务集成测试 | GATE 3: 全量 UT+API + E2E | 所有受影响服务 | 测试执行期间 |
| `staging` | 预发布验证 | 交付门禁: 冒烟 + 金丝雀 | 全量服务 (生产镜像) | 持续运行 |
| `production` | 生产环境 | 只读监控 | 全量服务 | 持久 |

## Provider 接口 (统一抽象)

每个 Provider 必须实现以下操作。框架代码只调用这些操作，不直接执行 docker/kubectl/gradle 命令:

```
interface EnvironmentProvider:
  
  # --- 生命周期 ---
  start(services: Service[]) → StartResult
    启动指定服务，等待健康检查通过。
    返回: {service_id: {status: "running", endpoint: "http://localhost:8081", pid/container_id: "..."}}
  
  stop(services: Service[]) → StopResult
    停止指定服务，清理资源。
    返回: {service_id: {status: "stopped"}}
  
  # --- 健康检查 ---
  health_check(service: Service, timeout_seconds: int = 30) → bool
    轮询服务的 health_check 端点，直到返回 200 或超时。
  
  wait_healthy(services: Service[], timeout_seconds: int = 120) → bool
    等待所有服务健康检查通过。任一超时返回 false。
  
  # --- 端点解析 ---
  get_endpoint(service: Service, port: int = null) → str
    返回服务可访问的 URL。
    例: local-process → "http://localhost:8081"
         docker-compose → "http://user-service:8080" (容器网络)
         k8s → "http://user-service.staging.svc.cluster.local:8080"
  
  # --- 诊断 ---
  get_logs(service: Service, tail: int = 100) → str
    获取服务最近 N 行日志。
  
  exec(service: Service, command: str) → ExecResult
    在服务上下文中执行命令 (如数据库迁移、种子数据加载)。
    local-process: 直接在 worktree 内执行
    docker: docker exec
    k8s: kubectl exec
  
  # --- 状态 ---
  status(services: Service[]) → StatusResult
    返回所有服务当前状态: running / stopped / unhealthy / error
```

## Provider 实现

### Provider 1: local-process

最简单的 Provider。服务以**本机进程**方式运行，适用于单仓库单体或微服务 co-location 场景。

```yaml
# 配置
provider: "local-process"

service_defaults:
  start_command: "{detected}"      # 从语言自动检测: ./gradlew bootRun / npm run dev / go run .
  stop_signal: "SIGTERM"
  health_check_timeout: 30
```

**操作映射:**

| 接口操作 | 实现 |
|---------|------|
| `start` | 在 worktree 内执行 `{start_command} &`，记录 PID |
| `stop` | `kill -{stop_signal} {pid}` |
| `health_check` | `curl -s {health_check_path}` 轮询 |
| `get_endpoint` | `http://localhost:{port}` |
| `get_logs` | `tail -n {n} {worktree}/logs/*.log` 或 stdout 重定向文件 |
| `exec` | 直接在 worktree 内执行命令 |

**适用场景:**
- 单体架构
- 微服务 co-location (所有服务在 `services/` 下)
- 快速本地开发迭代

**约束:**
- 需要本机安装所有语言的运行时 (JDK, Node, Go, Python)
- 端口冲突需要管理 (每个服务不同端口)
- 不隔离依赖 (共享本机 DB/Redis，或使用 Testcontainers)

### Provider 2: docker-compose

使用 Docker Compose 编排多服务。每个服务构建为容器镜像。

```yaml
# 配置
provider: "docker-compose"

service_defaults:
  dockerfile: "Dockerfile"         # 默认 Dockerfile 路径 (相对于 service_path)
  build_context: "{service_path}"  # 构建上下文
  health_check_timeout: 60

compose:
  file: "docker-compose.{tier}.yaml"  # 按环境层级自动选择
  project_name: "hw-{requirement_id}"
  network: "hw-integration"
```

**操作映射:**

| 接口操作 | 实现 |
|---------|------|
| `start` | `docker compose -f {compose_file} up -d {services}` |
| `stop` | `docker compose -f {compose_file} down` |
| `health_check` | `docker inspect {container} --format='{{.State.Health.Status}}'` |
| `get_endpoint` | `http://{service}:{port}` (容器网络) 或 `http://localhost:{mapped_port}` |
| `get_logs` | `docker compose logs --tail={n} {service}` |
| `exec` | `docker compose exec {service} {command}` |

**适用场景:**
- 团队已有 Docker 基础设施
- 服务有现成的 Dockerfile
- 集成测试需要隔离的网络环境

**compose 文件生成:**
- 由 hw-controller 在设计阶段生成 `docker-compose.integration.yaml`
- 基于 `service-registry.yaml` 中的服务列表和端口自动编排
- 用户可提供 `docker-compose.integration.override.yaml` 覆盖

### Provider 3: kubernetes

使用 Kubernetes 部署服务。适用于已有 K8s 集群的团队。

```yaml
# 配置
provider: "kubernetes"

service_defaults:
  namespace: "hw-{tier}"           # 按环境层级自动选择 namespace
  kubeconfig: "~/.kube/config"
  context: "{cluster_context}"
  image_registry: "{registry}/hw-{service_id}"
  image_tag: "{git_commit_sha}"
  health_check_timeout: 120

k8s:
  manifests_dir: "k8s/{tier}/"    # 按环境层级自动选择
  wait_for_rollout: true
  rollout_timeout: 300
```

**操作映射:**

| 接口操作 | 实现 |
|---------|------|
| `start` | `kubectl apply -f {manifests_dir}/{service}/` → `kubectl rollout status` |
| `stop` | `kubectl delete -f {manifests_dir}/{service}/` |
| `health_check` | `kubectl get pod -l app={service} -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}'` |
| `get_endpoint` | `http://{service}.{namespace}.svc.cluster.local:{port}` (集群内) 或 port-forward |
| `get_logs` | `kubectl logs --tail={n} -l app={service}` |
| `exec` | `kubectl exec -it deploy/{service} -- {command}` |

**适用场景:**
- 团队使用 Kubernetes 作为标准部署平台
- 需要生产环境 parity 的集成测试
- 金丝雀/灰度发布验证

**约束:**
- 需要 K8s 集群访问权限
- 镜像构建和推送需要 CI/CD 配合
- 比 local-process/docker-compose 启动慢

### Provider 对比

| 维度 | local-process | docker-compose | kubernetes |
|------|--------------|----------------|------------|
| 启动速度 | 秒级 | 分钟级 (构建镜像) | 分钟级 (推送+拉取镜像) |
| 隔离性 | 无 (共享 OS) | 容器隔离 | Pod 隔离 |
| 生产 parity | 低 | 中 | 高 |
| 依赖安装 | 需要所有运行时 | 只需 Docker | 只需 kubectl |
| 端口管理 | 手动 | 自动 (容器网络) | 自动 (Service/Ingress) |
| 适用团队 | 小型/单体 | 中型 | 大型/企业 |
| 工作流复杂度 | 最低 | 中 | 高 |

## 服务启动命令 (Per-Service Lifecycle)

每个服务通过 `service-registry.yaml` 声明自己的生命周期命令。Provider 在执行 `start()` 时使用这些命令:

```yaml
# service-registry.yaml 扩展字段
services:
  - id: "user-service"
    ...
    lifecycle:                          # 新增: 每个 Provider 可能有不同命令
      local-process:
        build: "./gradlew build -x test"
        start: "./gradlew bootRun"
        stop_signal: "SIGTERM"
        health_check: "/actuator/health"
        env:
          SPRING_PROFILES_ACTIVE: "dev"
          SERVER_PORT: "8081"
          
      docker-compose:
        dockerfile: "Dockerfile"
        build_context: "services/user-service"
        health_check: "/actuator/health"
        env:
          SPRING_PROFILES_ACTIVE: "docker"
          
      kubernetes:
        image: "registry.example.com/user-service"
        health_check: "/actuator/health"
        readiness_path: "/actuator/health/readiness"
        liveness_path: "/actuator/health/liveness"
```

**命令自动检测 (local-process，当 lifecycle 未配置时):**

| 语言 | 构建命令 | 启动命令 | 默认端口 |
|------|---------|---------|---------|
| java-gradle | `./gradlew build -x test` | `./gradlew bootRun` | 8080 |
| java-maven | `./mvnw compile -DskipTests` | `./mvnw spring-boot:run` | 8080 |
| node-npm | `npm ci` | `npm run dev` | 3000 |
| node-yarn | `yarn install` | `yarn dev` | 3000 |
| go | `go build ./...` | `go run .` | 8080 |
| python-poetry | `poetry install` | `poetry run uvicorn main:app` | 8000 |
| python-pip | `pip install -r requirements.txt` | `python -m uvicorn main:app` | 8000 |
| rust | `cargo build` | `cargo run` | 8080 |

## 配置 (config.yaml)

```yaml
# _bmad/config.yaml
hw:
  architecture: "microservices"

  # 环境 Provider 配置 — 按层级选择 Provider
  environments:
    worktree-local:
      provider: "local-process"           # 固定 (worktree 内永远是本地进程)
    
    integration:
      provider: "docker-compose"          # "local-process" | "docker-compose" | "kubernetes"
      # 不同 provider 的配置由 provider 实现解析
      compose:
        project_name: "hw-integration"
        network: "hw-net"
        generate_compose: true            # hw-controller 自动生成 compose 文件
    
    staging:
      provider: "kubernetes"
      k8s:
        namespace: "staging"
        context: "staging-cluster"
    
    production:
      provider: "kubernetes"
      k8s:
        namespace: "production"
        read_only: true                   # 生产环境只读
```

## 使用示例 (框架代码如何调用)

```
# 示例: 第一轮 API 测试 (worktree-local 环境)

1. 加载配置 → environments.worktree-local.provider = "local-process"
2. 加载 Provider 实现 → local-process
3. 获取服务 lifecycle → service-registry.yaml → user-service.lifecycle.local-process
4. provider.start([user-service])
   → cd services/user-service && ./gradlew bootRun &
   → 轮询 curl localhost:8081/actuator/health 直到 200
5. provider.get_endpoint(user-service)
   → "http://localhost:8081"
6. newman run api-tests.json --env-var baseUrl=http://localhost:8081
7. provider.stop([user-service])
   → kill SIGTERM {pid}


# 示例: 第三轮集成测试 (integration 环境)

1. 加载配置 → environments.integration.provider = "docker-compose"
2. 加载 Provider 实现 → docker-compose
3. provider.start(all_affected_services)
   → docker compose -f docker-compose.integration.yaml up -d
   → provider.wait_healthy(all_affected_services, timeout=120)
4. provider.get_endpoint(user-service)
   → "http://user-service:8080"  (容器网络)
5. newman run api-tests.json --env-var baseUrl=http://user-service:8080
6. npx playwright test e2e/ --baseURL=http://web-frontend:3000
7. provider.stop(all_services)
   → docker compose down


# 示例: staging 预发布验证

1. 加载配置 → environments.staging.provider = "kubernetes"
2. 服务已部署 (CI/CD 负责)，不需要 start
3. provider.health_check(all_services) → 确认健康
4. 冒烟测试 + 金丝雀分析
5. 不执行 stop (staging 持续运行)
```

## 与现有文档的关系

| 现有文档 | 变更方向 |
|---------|---------|
| `quality-gates.md` GATE 1 | `newman run` 命令中的 baseUrl 通过 `provider.get_endpoint()` 获取，不硬编码 localhost |
| `quality-gates.md` GATE 3 | `docker-compose` 命令替换为 `provider.start()` / `provider.stop()` |
| `task-decomposition.md` Step 3 | 第一/二/三轮 API 测试的环境表述，改为引用环境层级名而非具体技术 |
| `microservice-adaptation.md` | `integration_test_mode` 废弃，迁移到 `environments.integration.provider` |
| `worktree-management.md` | 服务搭建命令从 lifecycle 字段读取，不硬编码 `./gradlew` |
| `service-registry.yaml` schema | 新增 `lifecycle` 字段 |

## 新 Provider 的扩展方式

新增一种部署技术（如 Serverless、Nomad、Podman）只需:

1. 在 `environment-abstraction.md` 添加 Provider 实现章节
2. 实现 Provider 接口的 7 个操作
3. 在 `_bmad/config.yaml` 的 `environments` 配置块中引用新 provider 名称
4. 如果新 provider 改变了服务启动方式，在 `service-registry.yaml` 的 `lifecycle` 中添加对应的命令配置

不需要修改 `quality-gates.md`、`task-decomposition.md` 等框架核心文档。
