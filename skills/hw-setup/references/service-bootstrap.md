# 服务引导 (Service Bootstrap)

## 核心理念

微服务模式下，在 黑灯工厂 启动任何流程之前，必须确保所有服务处于**已知良好状态**——代码最新、环境可用、元数据已发现。这不是可选的准备工作，而是硬前置条件。

## 引导流程 (4 步)

### 第 1 步: 服务就绪检查 (Service Readiness Check)

**检查清单:**

```bash
# 对每个在 service-registry.yaml 中定义的服务执行

# 1. services/{service-id}/ 目录存在
test -d "services/{service-id}" || echo "MISSING: services/{service-id}"

# 2. 是一个 git 仓库
test -d "services/{service-id}/.git" || echo "NOT_A_REPO: services/{service-id}"

# 3. 当前在正确的分支上
cd services/{service-id} && git branch --show-current | grep -q "{base_branch}" || echo "WRONG_BRANCH"

# 4. 与 remote 同步 (无未推送的本地提交)
cd services/{service-id} && git status | grep -q "Your branch is up to date" || echo "NOT_SYNCED"

# 5. 无未提交的更改
cd services/{service-id} && git diff --quiet && git diff --cached --quiet || echo "HAS_UNCOMMITTED"
```

**如果服务不存在 → 自动克隆:**

```bash
# 从 service-registry.yaml 或 config 中读取 repo URL
git clone {repo_url} services/{service-id}
cd services/{service-id}
git checkout {base_branch}
```

**如果服务存在但未同步:**

```bash
cd services/{service-id}
git fetch origin
git checkout {base_branch}
git pull origin {base_branch}
```

### 第 2 步: 环境搭建 (Environment Setup)

对每个服务执行其语言特定的环境搭建:

| 服务语言 | 搭建命令 | 超时 |
|---------|---------|------|
| Java/Gradle | `cd services/{id} && ./gradlew build -x test` | 5 min |
| Java/Maven | `cd services/{id} && mvn install -DskipTests` | 5 min |
| TypeScript/npm | `cd services/{id} && npm ci` | 3 min |
| Python/pip | `cd services/{id} && pip install -r requirements.txt && pip install -r requirements-dev.txt` | 3 min |
| Go | `cd services/{id} && go mod download` | 2 min |

**端口冲突检测:**

```bash
# 检查每个服务的端口是否被占用
for svc in {service_ids}; do
  port=$(get_service_port $svc)
  if lsof -i :$port > /dev/null 2>&1; then
    echo "WARNING: Port $port is in use — service $svc may conflict"
  fi
done
```

### 第 3 步: 基线验证 (Baseline Verification)

在开始任何开发工作之前，运行每个服务的测试套件，确保基线是干净的:

```bash
# 对每个服务执行测试
for svc in {service_ids}; do
  echo "=== Verifying $svc ==="
  cd services/$svc
  {test_command} 2>&1 | tail -20
  if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "FAILED: $svc baseline tests"
  fi
done
```

**基线失败处理:**

| 失败类型 | 响应 |
|---------|------|
| 已知 flaky test (已在知识库记录) | 标记为 KNOWN_FLAKY，不阻塞 |
| 环境问题 (缺少依赖/配置) | 修复环境，重新验证 |
| 代码问题 (主分支上就有 broken test) | 警告 + 标记为 KNOWN_ISSUE，升级人工 |
| 全部服务都失败 | 怀疑是基础设施问题 (DB 不可用/网络) → 检查 docker-compose / 网络 |

### 第 4 步: 触发服务发现 (Trigger Discovery)

环境就绪后，触发 `hw-knowledge-agent` 的服务发现流程:

```
1. 扫描 services/ 目录 → 更新服务清单
2. 检测每个服务的技术栈 → 更新 service-registry.yaml
3. 提取 API 端点、DB Schema、依赖关系 → 生成服务知识文件
4. 构建服务依赖图 → 验证无循环依赖
5. 写入 knowledge-base/services/{id}/*.md
```

**服务发现必须产生:**
- `_bmad/memory/hw-shared/service-registry.yaml` — 机器可读的服务元数据
- `_bmad/memory/hw-shared/knowledge-base/services/{id}/overview.md` — 人类可读的服务概览
- `_bmad/memory/hw-shared/knowledge-base/services/{id}/api-endpoints.md`
- `_bmad/memory/hw-shared/knowledge-base/services/{id}/db-schema.md`

## 引导报告

引导完成后，输出一份汇总报告:

```markdown
# 服务引导报告 — {timestamp}

## 服务状态

| 服务 | 状态 | 分支 | Commit | 基线测试 | 端口 |
|------|------|------|--------|---------|------|
| user-service | ✅ READY | main | abc123 | 42/42 PASS | 8081 |
| order-service | ✅ READY | main | def456 | 38/38 PASS | 8082 |
| web-frontend | ✅ READY | main | ghi789 | 12/12 PASS | 3000 |
| notification-service | ⚠️ WARNING | main | jkl012 | 8/10 PASS (2 known flaky) | 8084 |

## 服务依赖图

```
user-service ←── order-service ←── web-frontend
     ↑               ↑
     └── notification-service
```

## 问题

- notification-service: 2 个已知 flaky test (JIRA-1234, JIRA-1235)
- 无循环依赖
- 所有端口可用，无冲突

## 下一步

所有服务就绪。可以开始需求澄清流程。
```

## 增量引导 (Incremental Bootstrap)

如果是再次运行（非首次），采用增量策略:

| 场景 | 操作 |
|------|------|
| 服务代码未变更 (commit SHA 相同) | 跳过环境搭建 + 基线验证 + 发现 |
| 服务代码有变更 | 重新执行该服务的: git pull → env setup → 基线验证 → 发现 (增量) |
| 新增服务 | 执行完整引导流程 (4 步) |
| 移除服务 | 从 registry 中移除，清理 worktree 目录 |

## 与 hw-controller 的约定

引导完成后，hw-controller 可以假设:
1. `service-registry.yaml` 是最新的（反映了当前代码状态）
2. 每个服务的基线测试是 PASS 的
3. 服务依赖图无循环
4. 所有服务的 API 端点、DB Schema、依赖关系已索引

**hw-controller 不应自行修改 service-registry.yaml。** 服务元数据的变更必须通过 hw-knowledge-agent 的发现流程或人工显式更新。
