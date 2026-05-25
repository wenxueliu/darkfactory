# Plan Parsing: 计划文件解析

## 目标

从计划文件中提取所有顶层任务、依赖关系和 QA 场景，构建可执行的任务列表。

## 计划文件位置

标准路径:
```
{project-root}/_bmad/memory/hw-shared/plans/{plan-name}.md
```

## 解析步骤

### 1. 读取计划文件

使用 Read 工具完整读取计划文件内容。

### 2. 识别任务区域

计划文件使用 Markdown 标题分段。任务位于 `## TODOs` 或 `## Tasks` 或 `## 任务列表` 的标题下。

### 3. 提取顶层任务复选框

**关键规则：仅提取顶层任务复选框，忽略嵌套/子复选框。**

顶层任务的特征：
- 直接位于 `## TODOs` (或等效标题) 下方
- 使用 `- [ ]` (未完成) 或 `- [x]` (已完成) 格式
- 左侧无缩进或仅有 `## TODOs` 的一级缩进

**必须忽略的内容：**
- Acceptance Criteria (验收标准) 下的复选框
- Evidence / 证据 下的复选框
- Definition of Done 下的复选框
- Final Checklist / 最终检查清单 下的复选框
- 任何缩进层级超过 2 级的复选框
- 代码块中的 `- [ ]` 字符串

### 4. 解析每个任务

对每个顶层任务提取：
- **任务描述**：`- [ ]` 后的文本内容，去除 checkbox 标记
- **任务 ID**：从描述中推断或分配序号 (task-1, task-2, ...)
- **完成状态**：`[ ]` = pending, `[x]` = completed
- **依赖声明**：任务描述中的显式依赖

### 5. 识别依赖声明

在任务描述中查找依赖关键字：
- "depends on" / "依赖于" + 任务名
- "after" / "在...之后" + 任务名
- "requires" / "需要" + 任务名
- "blocked by" / "被...阻塞" + 任务名
- "(depends on: task-X)" / "(依赖: task-X)"
- "输入来自" / "input from" + 任务名

### 6. 识别 QA 场景

部分任务包含 QA / verification 场景。查找：
- "QA:" / "验证:" 后的描述
- "How to verify:" / "如何验证:" 后的步骤
- "Acceptance:" / "验收:" 后的条件

### 7. 识别 Final Verification Wave

查找 `## Final Verification Wave` 或 `## 最终验证波` 标题下的任务。这些是审批关卡，不是常规实现任务。

### 8. 输出解析结果

输出结构化的任务分析报告。

## 示例

### 输入：计划文件摘录

```markdown
# Plan: user-auth-feature

## TODOs

- [ ] 实现用户注册 API (POST /api/auth/register)
  - Acceptance Criteria: 返回 JWT token
  - QA: curl -X POST /api/auth/register -d '{"email":"test@test.com","password":"Abc123!"}' 返回 201 + token

- [ ] 实现用户登录 API (POST /api/auth/login)
  - depends on: 实现用户注册 API (需要注册后才能测试登录)
  - QA: curl -X POST /api/auth/login -d '{"email":"test@test.com","password":"Abc123!"}' 返回 200 + token

- [ ] 添加密码强度验证 (最少8位，包含大小写字母和数字)
  - QA: 弱密码被拒绝，返回 400 + 错误信息

- [ ] 实现 Token 刷新 API (POST /api/auth/refresh)
  - depends on: 实现用户登录 API
  - QA: 使用有效 refresh token 获取新 access token

## Final Verification Wave

- [ ] F1: 逻辑审查 — 检查所有 API 的正确性和边界情况
- [ ] F2: 安全审查 — 检查认证流程的安全漏洞
- [ ] F3: 性能审查 — 检查 token 生成和验证的性能
```

### 输出：解析结果

```
TASK ANALYSIS:
- Plan: user-auth-feature
- Total top-level tasks: 4
- Completed: 0
- Remaining: 4

PARALLEL BATCH (no named dependencies):
  [task-1] 实现用户注册 API
    QA: curl POST /api/auth/register → 201 + token + JWT
  [task-3] 添加密码强度验证
    QA: 弱密码 → 400 + error message

SEQUENTIAL (named dependencies):
  [task-2] 实现用户登录 API
    Depends on: task-1 (需要注册后才能测试登录)
  [task-4] 实现 Token 刷新 API
    Depends on: task-2 (实现用户登录 API)

FINAL VERIFICATION WAVE:
  F1: 逻辑审查 (hw-reviewer-logic)
  F2: 安全审查 (hw-reviewer-security)
  F3: 性能审查 (hw-reviewer-performance)

EXECUTION PLAN:
  Wave 1 (parallel): task-1, task-3
  Wave 2 (parallel after Wave 1): task-2
  Wave 3 (parallel after Wave 2): task-4
  Wave Final: F1, F2, F3 (all parallel)
```

## 边界情况处理

### 已全部完成的计划

如果所有顶层任务都是 `- [x]`，直接进入 Final Verification Wave。

### 无 Final Verification Wave 的计划

如果计划中没有 Final Verification Wave 部分，完成所有实现任务后报告完成。不强制要求审查。

### 无 QA 场景的任务

不影响执行。在 4-Phase 验证中跳过 Phase C (Hands-On QA)。

### 任务描述跨多行

将续行合并到同一个任务描述中，直到遇到下一个 `- [ ]` 或 `- [x]`。

### 空计划

如果 `## TODOs` 下没有任务，报告 "Plan is empty — nothing to execute" 并退出。

## 常见错误

| 错误 | 纠正 |
|------|------|
| 将 Acceptance Criteria 下的复选框当作任务 | 仅提取直接位于 TODOs 标题下的一级 `- [ ]` |
| 将 Final Verification Wave 任务当作常规任务 | F1-F4 是审批关卡，不是实现任务 |
| 忽略了隐式依赖 | 除显式声明的依赖外，所有任务默认可并行 |
| 解析已完成任务为待办 | 检查 `[x]` vs `[ ]` |
