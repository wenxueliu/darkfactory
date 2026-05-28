# Worktree 管理 (Worktree Management)

## 核心理念

Worktree 是任务执行的**隔离容器**——每个任务在自己的 worktree 中独立开发、测试、审查，互不干扰。Worktree 管理的核心职责是: 创建干净的环境、验证基线、追踪状态、检测冲突、在任务完成后安全清理。

## Worktree 生命周期

```
                   ┌──────────────────┐
                   │     pending      │  任务已定义，等待调度
                   └────────┬─────────┘
                            │ 批次到达 + 依赖满足
                   ┌────────▼─────────┐
                   │    creating      │  git worktree add + 环境搭建
                   └────────┬─────────┘
                            │ 环境就绪 + 基线测试通过
                   ┌────────▼─────────┐
                   │     running      │  Worktree Controller 执行 TDD
                   └────────┬─────────┘
                            │ 所有门禁通过
                   ┌────────▼─────────┐
                   │    reviewing     │  安全/逻辑/性能审查
                   └────────┬─────────┘
                            │ P0/P1/P2 全部解决
              ┌─────────────┴─────────────┐
              ▼                           ▼
    ┌──────────────────┐       ┌──────────────────┐
    │      done        │       │ done_with_concerns│
    │ (所有门禁通过)    │       │ (有已知风险，已记录)│
    └────────┬─────────┘       └────────┬─────────┘
             │                          │
             └──────────┬───────────────┘
                        │ 所有 worktree DONE → merge
              ┌─────────▼─────────┐
              │      merged       │  git merge + 解决冲突
              └─────────┬─────────┘
                        │
              ┌─────────▼─────────┐
              │     cleaned       │  git worktree remove
              └───────────────────┘

异常路径:
  creating → (环境搭建失败) → blocked (记录原因，人工介入)
  running  → (依赖不可用) → needs_context (请求上下文)
  running  → (TDD 循环超限) → blocked (人工介入)
  running  → (超时) → blocked (检查是否卡死)
  reviewing → (P0 无法修复) → blocked (人工决策)
  any      → (手动取消) → abandoned → cleaned
```

## 创建与初始化 (Create & Setup)

### 1. 安全检查

创建 worktree 之前:

- [ ] `.gitignore` 中包含 `.worktree/`（验证: `grep '\.worktree' .gitignore`）
- [ ] 主分支无未提交的更改（验证: `git status --porcelain` 为空或在 worktree_base 之外）
- [ ] 磁盘空间充足（验证: `df -h {worktree_base}` 剩余 > 2GB）
- [ ] 没有同名 worktree 存在（验证: `git worktree list | grep sw-task-{id}`）

### 2. 创建命令

```bash
# 从项目根目录执行
cd {project-root}

# 创建 worktree（在新分支上）
git worktree add {worktree_base}/sw-task-{task_id} -b sw-task-{task_id} {base_branch}

# 进入 worktree
cd {worktree_base}/sw-task-{task_id}
```

### 3. 环境搭建

环境搭建命令从 `service-registry.yaml` → `lifecycle.{provider}.build` 读取，不硬编码。

详见 `environment-abstraction.md`。

| 语言 | 默认构建命令 (lifecycle 未配置时自动检测) |
|------|------------------------------------------|
| Java/Maven | `./mvnw compile -DskipTests` |
| Java/Gradle | `./gradlew build -x test` |
| Node.js/npm | `npm ci` |
| Node.js/yarn | `yarn install` |
| Python/pip | `pip install -r requirements.txt && pip install -r requirements-dev.txt` |
| Python/poetry | `poetry install` |
| Go | `go mod download` |
| Rust | `cargo build` |

### 4. 基线验证

在开始任何开发之前，运行已有测试套件确认环境正确。

测试命令从 `service-registry.yaml` → `lifecycle.{provider}.test` 读取。
默认按语言自动检测:

| 语言 | 默认测试命令 |
|------|------------|
| Java | `./gradlew test` 或 `./mvnw test` |
| Node.js | `npm test` |
| Python | `pytest` |
| Go | `go test ./...` |
| Rust | `cargo test` |

**基线测试必须 100% PASS。** 如果有失败:
1. 检查是否是环境问题（依赖版本、配置缺失）
2. 如果是主分支已有的 broken test → 标记为已知问题，记录到 worktree registry
3. 如果是环境搭建问题 → 修复环境，重新验证
4. 如果无法修复 → 标记 worktree 为 `blocked`，升级到人工

### 5. 注册

更新 worktree-registry.yaml:

```yaml
worktrees:
  sw-task-{NNN}:
    branch: "sw-task-{NNN}"
    task_id: "sw-{NNN}"
    status: "running"
    wave: {n}
    created_at: "{timestamp}"
    started_at: "{timestamp}"
    baseline_test_passed: true
    path: "{worktree_base}/sw-task-{NNN}"
    environment:
      node_version: "{version}"
      java_version: "{version}"
      dependencies_installed: true
```

## 冲突检测 (Conflict Detection)

### 文件级冲突预测

在任务开始前，分析任务之间可能修改的共享文件:

| 场景 | 检测方式 | 风险 |
|------|---------|------|
| 两个任务修改同一个文件 | 分析任务涉及的组件路径 | 高风险 — 合并冲突 |
| 两个任务修改同一 API 的 schema | 分析设计文档 API 端点表 | 高风险 — 接口不一致 |
| 两个任务修改不同文件但共享 import | 分析 import 图 | 中风险 — 编译错误 |
| 两个任务修改不同模块 | 无共享路径 | 低风险 |

**冲突预防:**
- 高风险任务不应在同一批次并行——调整批次分配
- 如果必须并行（关键路径）——指定合并顺序: "B 合并到 A 之后"

### 运行时冲突监控

在 worktree 执行期间，定期检查:

```bash
# 检查 worktree 分支是否偏离主分支
git log --oneline {base_branch}..HEAD | wc -l

# 检查与主分支的文件冲突
git diff {base_branch} --stat
```

如果 worktree 已经偏离主分支 > 50 commits 或有 > 20 个文件冲突 → 发出警告，建议提前做一次 `git merge {base_branch}`（在 worktree 内部）。

## 状态追踪 (Status Tracking)

### Worktree Controller 报告处理

Worktree Controller 通过更新 worktree-registry.yaml 报告状态:

| 状态 | 触发条件 | 总控响应 |
|------|---------|---------|
| `running` | 任务开始执行 | 记录 started_at |
| `needs_context` | 缺少信息或上下文 | 从共享内存提供上下文；如果共享内存无 → 升级人工 |
| `blocked` | 遇到无法自动解决的问题 | 分析原因: 依赖/环境/设计缺陷 → 对应处理 |
| `reviewing` | TDD 完成，进入审查 | 触发安全/逻辑/性能并行审查 |
| `done` | 所有门禁通过 | 标记完成，检查是否所有 worktree 都 DONE |
| `done_with_concerns` | 通过但有已知风险 | 记录 concerns 到 registry，人类评估 |
| `abandoned` | 手动取消或不可恢复 | 清理 worktree，标记任务需重新分配 |

### 心跳检查

如果 worktree > 30 分钟没有状态更新:

1. 检查 worktree 进程是否还在运行
2. 检查最近的 git commit 时间
3. 如果无活动 > 60 分钟 → 标记 `blocked`（可能卡死），升级人工

## 合并 (Merge)

当所有 worktree 达到 `done` 或 `done_with_concerns` 后，按依赖顺序合并:

```bash
# 1. 切回主分支
cd {project-root}
git checkout {base_branch}

# 2. 按 wave 顺序合并 (wave 1 → wave 2 → wave 3)
for worktree in wave_1_done:
    git merge sw-task-{id} --no-ff -m "merge(sw-task-{id}): {task_name}"

# 3. 运行全量回归测试
mvn test  # or equivalent

# 4. 如果回归通过 → 继续下一 wave
# 5. 如果回归失败 → 定位问题 worktree，回滚该 merge
```

**冲突解决优先级:**
1. 自动合并成功 → 继续
2. 自动合并有冲突 → 分析冲突文件，用 `git mergetool` 或手动解决
3. 如果冲突无法自动解决 → 升级到人工，附带冲突文件和两个分支的 diff

## 清理 (Cleanup)

### 正常清理（任务完成后）

```bash
# 1. 确认已合并
git branch --merged {base_branch} | grep sw-task-{id}

# 2. 移除 worktree
git worktree remove {worktree_base}/sw-task-{task_id}

# 3. 删除分支 (可选，保留用于审计)
git branch -d sw-task-{task_id}

# 4. 更新 registry
# status: "merged" → "cleaned"
```

### 异常清理（任务失败/取消）

```bash
# 1. 强制移除 worktree
git worktree remove --force {worktree_base}/sw-task-{task_id}

# 2. 删除分支
git branch -D sw-task-{task_id}

# 3. 清理 worktree 目录下的残留文件
rm -rf {worktree_base}/sw-task-{task_id}

# 4. 更新 registry
# status: "blocked|abandoned" → "cleaned"
```

### 清理检查清单

- [ ] `git worktree list` 不包含已清理的 worktree
- [ ] `{worktree_base}/sw-task-{task_id}/` 目录已删除
- [ ] worktree-registry.yaml 中状态已更新为 `cleaned`
- [ ] 磁盘空间恢复正常

## 过渡门禁

Worktree 管理就绪，可以开始执行的条件:

- [ ] 所有 `pending` 状态的 worktree 创建成功
- [ ] 每个 worktree 环境搭建完成，依赖安装成功
- [ ] 基线测试 100% PASS（或已知失败已记录）
- [ ] worktree-registry.yaml 全部注册完成
- [ ] 冲突检测完成，高风险任务已调整批次
- [ ] `.gitignore` 验证通过（`.worktree/` 不会被提交）

**完成确认语:** "{N} 个 worktree 已创建，环境就绪，基线测试通过。冲突检测完成，{M} 个高风险依赖已调整。准备好分发任务到 worktree controller 了吗？"
