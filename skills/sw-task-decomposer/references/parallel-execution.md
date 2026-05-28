# 并行执行协调 (Parallel Execution Coordination)

## 核心理念

并行执行是黑灯工厂的核心效率来源——多个 worktree 同时推进，每个 worktree 中 TDD Agent + Reviewer Agent 独立运作。协调器的职责是: **按依赖图分批调度、监控心跳、聚合进度、检测死锁、在遇到阻塞时精准升级**。

## 执行流程 (3 个循环)

### 主循环: 批次调度 (Wave Dispatch Loop)

```
                  ┌──────────────────────┐
                  │ 读取 tasks.yaml      │
                  │ 获取所有 wave        │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │ 当前 wave 所有任务    │
                  │ 依赖是否已满足?       │
                  └──────────┬───────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
        依赖满足                       依赖未满足
   ┌──────────────┐              ┌──────────────┐
   │ 分配 Worktree │              │ 等待依赖 wave │
   │ Controller    │              │ 完成 (轮询)   │
   │ (并行启动)    │              └──────────────┘
   └──────┬───────┘
          │
   ┌──────▼───────┐
   │ 监控循环      │ ← 心跳检查 + 状态聚合 + 阻塞处置
   │ (Monitor Loop)│
   └──────┬───────┘
          │
   ┌──────▼───────┐
   │ 当前 wave     │
   │ 全部 DONE?    │
   └──────┬───────┘
          │
   ┌──────▼───────┐
   │ 下一 wave     │
   │ 或 全部完成   │
   └──────────────┘
```

### 调度策略 (Dispatch Strategy)

**1. 批次前置检查:**

每个 wave 启动前检查:

- [ ] 上一 wave 所有任务 DONE（或 DONE_WITH_CONCERNS + 人类批准）
- [ ] 无上一 wave 的 P0/P1 问题遗留
- [ ] 当前 wave 所有任务的依赖已满足
- [ ] 系统资源足够（见并发限制）

**2. 任务分发:**

对当前 wave 中的每个任务，启动一个 Worktree Controller:

```
# 并行启动（不等待上一个完成）
Worktree Controller 1 ← Task sw-001 (wave 1)
Worktree Controller 2 ← Task sw-002 (wave 1)  同时启动
Worktree Controller 3 ← Task sw-003 (wave 1)  同时启动
Worktree Controller 4 ← Task sw-004 (wave 1)  同时启动
```

每个 Worktree Controller 收到:
- 任务定义 (来自 tasks.yaml)
- Worktree 路径
- 绑定的 UT/API/E2E 测试用例
- 审查要求 (security/logic/performance)

**3. 调度优化:**

| 场景 | 优化策略 |
|------|---------|
| 关键路径任务 | 优先分配资源（更多重试次数、更低的超限阈值） |
| 高风险任务 (多个高风险依赖) | 排在 wave 中优先执行，提前暴露问题 |
| 短任务 (< 30min) | 可以在同一 wave 中启动额外任务（如果并行度有余量） |
| 长任务 (> 2h) | 提高心跳检查频率，防止卡死后发现太晚 |

### 监控循环 (Monitor Loop)

**轮询频率:**

| 阶段 | 频率 | 原因 |
|------|------|------|
| TDD 执行中 | 每 5 分钟 | 平衡及时性和 token 消耗 |
| 审查中 | 每 3 分钟 | 审查通常较快 |
| 刚启动 (< 10min) | 每 2 分钟 | 早期问题快速暴露 |
| 全部完成，等待 merge | 每 10 分钟 | 被动等待 |

**每次轮询执行:**

1. 读取所有 running 状态的 worktree-registry 条目
2. 检查状态变化
3. 处理异常状态
4. 更新 global-state.yaml

**状态聚合:**

```yaml
# _context/memory/sw-controller/global-state.yaml
phase: execution
wave: {current_wave}
started_at: "{timestamp}"
last_updated: "{timestamp}"

summary:
  total_tasks: {n}
  completed: {n}
  running: {n}
  pending: {n}
  blocked: {n}
  overall_progress: "{pct}%"

waves:
  - wave: 1
    tasks: ["sw-001", "sw-002", "sw-003"]
    done: ["sw-001", "sw-002"]
    running: ["sw-003"]
    blocked: []
  - wave: 2
    tasks: ["sw-004", "sw-005"]
    status: "waiting_for_wave_1"

blockers:
  - task_id: "sw-003"
    status: "needs_context"
    description: "{具体缺少什么信息}"
    escalated: false
    escalated_at: null

cost:
  estimated_total: ${n}
  spent_so_far: ${n}
  budget_remaining: ${n}
```

### 异常处理 (Exception Handling)

**状态 → 响应映射:**

| Worktree 状态 | 总控响应 | 自动重试? |
|--------------|---------|----------|
| `needs_context` | 1. 查 shared memory 2. 查 knowledge base 3. 无结果 → 升级人工 | 否 (等上下文) |
| `blocked — 环境问题` | 1. 重建 worktree 环境 2. 重试 2 次 3. 仍失败 → 升级人工 | 是 (最多 2 次) |
| `blocked — 测试基线失败` | 1. 分析失败日志 2. 如果主分支已知问题 → 记录并继续 3. 否则 → 升级人工 | 否 |
| `blocked — 依赖未满足` | 等待依赖任务完成 → 通知 Worktree Controller 继续 | 否 (自动恢复) |
| `blocked — TDD 循环超限` | 超过 `min_iteration_before_human` → 升级人工 | 否 |
| `blocked — 超时 (> 60min 无更新)` | 1. 检查进程 2. 如果进程死 → 重启 worktree controller 3. 如果仍在运行 → 延长超时 | 是 (最多 1 次重启) |
| `done_with_concerns` | 1. 记录 concerns 2. 如果 P0/P1 concern → 升级人工 3. 如果 P2/P3 → 记录并继续 | 否 |

**升级格式:**

```
⚠️ 任务 {task_id} 需要人工介入

状态: {status}
问题: {具体描述}
上下文: {相关日志/文件路径}
已尝试: {已执行的自动修复步骤}

选项:
A) {建议选项 1}
B) {建议选项 2}
C) 自定义方案

💡 推荐: {选项 X}，因为 {理由}
```

### 死锁检测 (Deadlock Detection)

**检测条件:**
- 两个或多个任务同时 `needs_context`
- 且每个任务等待的上下文在另一个任务中

**检测算法:**
```
每 10 分钟检查:
  对每对 (task A, task B):
    如果 A.needs_context 且 A 等待的上下文在 B 中
    且 B.needs_context 且 B 等待的上下文在 A 中
    → DEADLOCK DETECTED

响应:
  1. 选择其中一个任务先解阻塞:
     - 选择接近完成的任务 (progress 更高)
     - 或选择依赖更少的任务
  2. 为该任务提供最佳可用的部分上下文
  3. 如果仍无法解决 → 两个任务都升级人工
```

### 进度报告 (Progress Reporting)

**向人类报告的频率:**

| 场景 | 频率 |
|------|------|
| 正常推进 | 每个 wave 完成时 + 每小时摘要 |
| 有任务 blocked | 立即 + 每小时摘要 |
| 成本接近预算 80% | 立即提醒 |
| 所有任务完成 | 立即 + 最终报告 |

**进度报告格式:**

```
📊 执行进度报告 — {timestamp}

Phase: Execution | Wave: {current}/{total}
Progress: {pct}% ({done}/{total} tasks)

✅ Done ({n}):
  - sw-001: {name} ({duration})
  - sw-002: {name} ({duration})

🔄 Running ({n}):
  - sw-003: {name} — {current_phase} ({elapsed})
  - sw-004: {name} — {current_phase} ({elapsed})

⏳ Pending ({n}):
  - sw-005: {name} — 等待 wave {n}

🚫 Blocked ({n}):
  - sw-006: {name} — {reason} — {action_taken}

💰 Cost: ${spent} / ${budget} budget

🔜 Next: wave {n} — {n} tasks ready
```

## 过渡门禁

并行执行完成，可以进入合并阶段的条件:

- [ ] 所有 worktree 状态为 DONE 或 DONE_WITH_CONCERNS
- [ ] 所有 blocked 任务已解决 (人工介入 + 决策)
- [ ] 所有 wave 的所有任务已完成
- [ ] 成本在预算范围内（或超支已由人工批准）
- [ ] global-state.yaml 中无未解决的 blockers

**完成确认语:** "所有 {N} 个任务执行完成。{M} 个 DONE，{K} 个 DONE_WITH_CONCERNS。总耗时 {duration}，总成本 ${cost}。准备好进入合并阶段吗？"
