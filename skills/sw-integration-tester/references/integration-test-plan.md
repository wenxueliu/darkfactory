# 集成测试计划模板

## 使用说明

此模板在 TDD 两层测试（UT + API）通过后，代码合并到主分支之前使用。确保各 worktree 产出的代码集成后不相互破坏。

写入 `{project-root}/_context/memory/sw-shared/tests/integration-plan-{requirement_id}.md`

---

# 集成测试计划: {需求标题}

**计划ID:** `{ITEST-YYYYMMDD-NNN}`
**关联需求:** `{REQ-YYYYMMDD-NNN}`
**关联任务:** `{task IDs from tasks.yaml}`
**状态:** `draft | in_progress | passed | failed`

## 1. 集成范围

### 涉及的 Worktree / 模块

| Worktree | 任务 | 修改的模块 | 新增的 API |
|----------|------|-----------|-----------|
| {wt-1} | {task-1} | {modules} | {endpoints} |
| {wt-2} | {task-2} | {modules} | {endpoints} |

### 集成风险矩阵

| 集成点 | 风险 | 验证方法 |
|--------|------|---------|
| {模块 A} ← → {模块 B} | {可能的冲突/不一致} | {测试方法} |

## 2. 集成测试用例

### IT-1: {测试名称}

**前置条件:** {环境状态、数据状态}
**测试步骤:**
1. {步骤 1}
2. {步骤 2}
**预期结果:** {具体的、可验证的结果}
**清理:** {测试后如何恢复环境}

### IT-2: {测试名称}

**前置条件:** {环境状态、数据状态}
**测试步骤:**
1. {步骤 1}
**预期结果:** {具体的、可验证的结果}

## 3. 回归测试检查

| 已有功能 | 是否受集成影响 | 回归测试 | 状态 |
|---------|--------------|---------|------|
| {功能名} | Y/N | {测试用例} | PASS/FAIL/SKIP |

## 4. 性能回归

| 指标 | 基线值 | 集成后值 | 偏差 | 是否阻塞 |
|------|--------|---------|------|---------|
| {指标名} | {baseline} | {actual} | ±{pct}% | Y/N |

## 5. 数据迁移验证

- [ ] 数据库迁移在集成环境执行成功
- [ ] 旧数据与新代码兼容（向后兼容验证）
- [ ] 回滚迁移在集成环境执行成功

## 6. 集成测试结果

```
PASS: {N}/{total} cases passed
FAIL: {N}/{total} cases failed
SKIP: {N}/{total} cases skipped
```

**阻塞项:**
- {列出所有 FAIL 的用例及原因}

### 6.1 API 测试 (Newman, 硬执行)

`sw-integration-tester` 必须在集成测试阶段通过 `python scripts/newman_runner.py --requirement-id {requirement_id}` 调用 newman。**此步骤不可跳过、不可选做。**

通过标准（全部满足才视为 PASS）:
- `newman run` exit code == 0
- JUnit XML 解析的 `failures == 0` 且 `errors == 0`
- `test-results.yaml` 的 `api_tests.{requirement_id}` 段已写入，含 `status: PASS`

退出码语义（脚本返回）:
| 退出码 | 含义 | 路由 |
|-------|------|------|
| 0 | 全部通过 | 进入下一步 |
| 2 | PRECHECK_FAILED (collection/env 缺失) | 回 sw-controller → sw-e2e-designer 补产出 |
| 3 | NEWMAN_MISSING (newman 未安装) | 升级到人工安装 |
| 4 | FAIL (newman 报告失败) | 诊断 → 修代码或修测试数据 |
| 5 | PARSE_FAILED (JUnit 解析异常) | 升级到人工（通常 newman/工具链不匹配） |
| 6 | 内部错误 | 重试一次，仍失败则升级人工 |

**反模式**:
- "newman 没跑但其他测试过了，所以整体 PASS" — 错误，newman 是硬门禁
- "JSON 文件不存在，我直接看代码审过了" — 错误，必须有可执行测试
- "本地能跑就行，不必每次 newman" — 错误，每次集成测试都必须跑 newman

## 7. 集成门禁

- [ ] 所有 IT 用例 PASS 或 SKIP（有合理理由）
- [ ] 回归测试全部 PASS
- [ ] 性能回归在可接受范围内
- [ ] 数据迁移验证通过

```
PASS: → 进入交付阶段
FAIL: → 修复 FAIL 项后重跑。最大重试 2 轮。
```
