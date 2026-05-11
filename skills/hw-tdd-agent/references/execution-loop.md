# 执行循环 (Execution Loop)

## EXPLORE → PLAN → DECIDE → EXECUTE → VERIFY

每一个 TDD 周期和每一项独立的实现任务都遵循此五阶段循环。循环确保理解、规划、执行和验证的系统性覆盖。

---

## Phase 1: EXPLORE (探索)

**目标:** 充分理解代码库上下文，明确变更范围和影响。

**做什么:**
1. 阅读任务定义和验收标准
2. 读取相关源代码文件（现有模块、测试、配置）
3. 理解数据流：输入从哪里来，输出到哪里去
4. 识别所有受影响的文件和模块
5. 检查是否存在类似的现有实现作为参考模式
6. 确认测试框架和工具链可用

**工具:**
- `grep` / `Grep` — 搜索引用、模式、符号
- `read` / `Read` — 读取文件和配置
- `glob` / `Glob` — 查找相关文件
- `git log` — 理解变更历史
- 代码库探索 agent（可并行启动 2-3 个）

**如何知道此阶段完成:**
- 你能够列出所有需要修改的文件
- 你能够列出所有需要新增的文件
- 你理解了数据流和模块依赖关系
- 你识别出了潜在的风险区域

**时间预算:** 对于典型任务，此阶段应在 2-5 分钟内完成。如果超过 10 分钟仍在探索，说明探索范围过大——缩小到核心路径。

---

## Phase 2: PLAN (规划)

**目标:** 生成可执行的变更计划，明确每个变更的边界和依赖。

**做什么:**
1. 列出所有要修改的文件（路径 + 修改类型）
2. 列出所有要新增的文件（路径 + 内容概要）
3. 识别变更之间的依赖关系（A 必须在 B 之前完成）
4. 估算复杂度（trivial / simple / moderate / complex）
5. 确定是否需要创建 TODO list（2+ 步骤时强制创建）
6. 确定是否需要升级到 worktree-controller（complex 多文件变更）

**输出格式:**
```
Plan:
1. references/ut-red.md — 新增，UserService 单元测试 (RED)
2. src/services/user_service.py — 修改，添加 create_user 方法 (GREEN)
3. src/services/user_service.py — 修改，提取 validate_email (REFACTOR)
4. references/api-red.md — 新增，POST /users API测试 (RED)
5. src/api/users.py — 修改，添加 POST /users 端点 (GREEN)

依赖: 1→2→3, 4→5。1 和 4 可并行。
复杂度: simple。不需要升级。
```

**决策门禁 (DECIDE 前置):**
- 变更是否影响公开 API？→ 确认向后兼容性
- 变更是否需要数据库迁移？→ 纳入迁移脚本
- 变更是否触及安全边界？→ 规划安全审查触发
- 变更是否涉及多个模块/服务？→ 考虑升级到 controller

**如何知道此阶段完成:**
- 你有一个清晰的、有序的变更列表
- 你了解变更之间的依赖关系
- 你已决定是直接执行还是升级

---

## Phase 3: DECIDE (决策)

**目标:** 根据任务复杂度和影响范围，选择执行策略。

**决策矩阵:**

| 场景 | 决策 | 理由 |
|------|------|------|
| 单一文件，少量修改 (<=50行) | 直接执行 | 开销极小，直接做更快 |
| 单一文件，大量修改 (>50行) | 直接执行 + TODO list | 需要步骤追踪但不需要协调 |
| 多个文件，同模块 (2-5文件) | 直接执行 + TODO list | 在 tdd-agent 范围内 |
| 多个文件，跨模块 (>5文件) | 考虑升级到 worktree-controller | 可能需要并行 worktree 协调 |
| 架构变更 | 升级到 worktree-controller | 需要跨 agent 协调审查 |
| 仅测试 | 直接执行 | tdd-agent 的核心职责 |

**升级决策检查清单:**
- [ ] 变更是否跨多个服务/模块边界？
- [ ] 变更是否需要其他 agent（reviewer）介入？
- [ ] 变更是否需要修改公开 API contract？
- [ ] 变更是否包含数据库 schema 修改？
- [ ] 变更是否需要新增第三方依赖？

2 个及以上 YES → 升级到 worktree-controller。

**如果升级:** 附带完整的 EXPLORE 和 PLAN 输出给上层 agent。

**如何知道此阶段完成:**
- 你已明确选择执行策略
- 如需升级，已完成升级消息

---

## Phase 4: EXECUTE (执行)

**目标:** 严格按照 TDD 铁律执行变更。

**TDD 执行顺序:**
```
Layer 1: Unit Tests
  RED   → 写失败的单元测试
  GREEN → 写最小实现让测试通过
  REFACTOR → 重构代码，保持测试绿色

Layer 2: API Tests (Layer 1 100% 通过后)
  RED   → 写失败的 API 测试
  GREEN → 写 API 实现让测试通过
  REFACTOR → 重构，保持所有测试绿色
```

**执行原则:**
- **外科手术式变更** — 每次只改最小必要的内容
- **RED 优先** — 永远先写失败的测试；如果不先看到测试失败，就不能写生产代码
- **最简实现** — 只写让测试通过的最少代码；不添加"将来可能需要"的功能
- **实时进度报告** — 每完成一个 RED/GREEN/REFACTOR 阶段，简短报告

**如果执行中遇到障碍:**
- 参考 `autonomous-execution.md` 中的升级决策树
- 不要跳过 TDD 步骤来绕过障碍
- 如果测试环境有问题，先修复测试环境

**禁止:**
- 在 RED 之前写 GREEN
- 跳过 REFACTOR（即使是简单实现也可以审视命名、结构）
- 在 Layer 1 完成前开始 Layer 2
- 一次写多个测试（一次一个行为）

**如何知道此阶段完成:**
- 所有计划的文件已修改/创建
- Layer 1 全部测试 100% 通过
- Layer 2 全部测试 100% 通过
- REFACTOR 已执行并保持所有测试绿色

---

## Phase 5: VERIFY (验证)

**目标:** 系统性验证变更的正确性和完整性。

**验证步骤（必须全部执行）:**

1. **诊断检查 (Diagnostics)**
   - 对所有修改过的文件运行 `lsp_diagnostics`
   - 零新增错误或警告（与变更前的基线比较）
   - 如果诊断报告错误，返回 EXECUTE 修复

2. **构建验证 (Build)**
   - 运行项目构建命令（如 `npm run build`, `make`, `go build ./...`）
   - 构建必须返回 exit code 0
   - 如果构建失败，返回 EXECUTE 修复

3. **测试运行 (Tests)**
   - 运行 ALL 测试，不仅仅是新增的
   - 验证没有回归：
     ```
     UT layer:  X / X  PASS  (0 failures)
     API layer: Y / Y  PASS  (0 failures)
     ```
   - 如果任何测试失败，返回 EXPLORE 分析失败原因

4. **TODO 清理 (TODO Cleanup)**
   - 确认所有 TODO 项标记为 completed
   - 没有遗漏的步骤

**验证失败处理:**
```
VERIFY 失败
  │
  ├── 第1次失败 → 返回 EXPLORE，分析根因
  │
  ├── 第2次失败 → 返回 EXPLORE，尝试不同方法
  │
  └── 第3次失败 → 升级到 strategic-advisor
      附带：3次尝试各做了什么、为什么失败、当前状态
```

**如何知道此阶段完成:**
- Diagnostics 干净（零新增错误/警告）
- Build exit code = 0
- ALL tests PASS (UT + API)
- 所有 TODO 标记为 completed

---

## 循环边界

### 何时退出循环（成功）
- VERIFY 阶段全部通过
- 所有任务完成
- 报告输出已生成

### 何时循环回去
- VERIFY 发现测试失败
- VERIFY 发现构建错误
- VERIFY 发现新增 diagnostic 问题

### 最大迭代次数
- 每个 TDD 步骤 (RED/GREEN/REFACTOR) 最多 2 次重试
- 整个 EXECUTE → VERIFY 循环最多 3 次重试
- 超过上限 → 升级到 strategic-advisor

### 何时升级
参考 `failure-escalation.md` 获取完整升级协议。
