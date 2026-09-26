# Requirements Tracker Update

## Purpose

此文档定义如何更新解析后的 `paths.artifact_targets.tracker`。sw-requirements-clarifier 是第一个写入者——在完成需求澄清和规格文档后，将需求条目写入 tracker。

## Resolved Paths

- Tracker：`paths.artifact_targets.tracker`
- Requirement document：`paths.artifact_targets.requirement_document`
- Config：`paths.config_file`
- 如果 tracker 不存在且没有调用方提供的初始化模板，只记录 `NOT_FOUND` 并提示初始化；不要在未声明目标时凭空创建另一套 tracker。

## Tracker File Path

```
paths.artifact_targets.tracker
```

## Operation: Create or Append Requirement Entry

### Step 1: Read the tracker

读取 `paths.artifact_targets.tracker`。

### Step 2: Determine mode

- **Create mode（首次使用）**: 文件只有模板注释和 `# TODO` 占位行，`requirements:` 列表下无实际条目。
- **File missing（文件不存在）**: tracker 尚未初始化。若调用方提供 tracker 初始化模板，按该模板从零创建；否则记录 `NOT_FOUND` 并提示初始化，不把缺失伪装成成功写入。
- **Append mode（已有需求）**: `requirements:` 列表下已有至少一个非注释的需求条目。

### Step 3: Build the new entry

从刚完成的需求规格文档中提取字段：

| Tracker 字段 | 数据来源 | 示例值 |
|-------------|---------|--------|
| `id` | 需求文档头部元数据的 `需求ID` 字段 | `REQ-20260526-001` |
| `title` | 需求文档 H1 标题 | `用户登录优化` |
| `description` | `section-id: problem_statement` 章节的 1-3 句摘要 | 见规格文档 |
| `business_domain` | `paths.config_file` → `sw.business_domain` | `general` |
| `priority` | `section-id: value_assessment` 章节的「综合优先级」 | `P1` |
| `created_at` | 今天日期 `YYYY-MM-DD` | `2026-05-26` |
| `updated_at` | 同上 | `2026-05-26` |
| `current_phase` | `ideation` | `ideation` |
| `status` | 推导（见下方规则） | `active` |

> 按 frontmatter、`section-id` 或字段标签定位取值，**不要按行号**。行号会随模板演进而失效；`section-id` 才是契约，标题和编号只是展示文本（见 `docs/document-contracts.md`）。

### Step 4: Build phases block

```yaml
phases:
  ideation:
    status: done
    artifacts:
      - paths.artifact_targets.requirement_document
    completed_at: '{today}'
  value_assessment:
    status: pending
    artifacts: []
    completed_at: null
  design:
    status: pending
    artifacts: []
    completed_at: null
  decomposition:
    status: pending
    artifacts: []
    completed_at: null
  execution:
    status: pending
    progress:
      tasks_total: 0
      tasks_done: 0
      worktrees_active: 0
      tasks_blocked: 0
    artifacts: []
    completed_at: null
  merge:
    status: pending
    artifacts: []
    completed_at: null
  test:
    status: pending
    artifacts: []
    completed_at: null
  delivery:
    status: pending
    artifacts: []
    completed_at: null
```

### Step 5: Derive overall status

```
任一 phase.status == blocked                → blocked
任一 phase.status == in_progress             → active
所有非 skipped phase.status == done          → done
所有 phase.status == pending                 → pending
```

新建时：仅 `ideation` 为 `done`，其余为 `pending` → 派生 `status: active`。

### Step 6: Write back

- **Create mode**: 删除 `# TODO` 行和所有注释的示例条目，将新条目作为 `requirements:` 的第一个列表项写入。
- **Append mode**: 在 `requirements:` 列表末尾追加新条目（保持已有条目不变）。

### Step 7: 生成 ID 的规则

- 格式：`REQ-YYYYMMDD-NNN`
- `YYYYMMDD` = 当天日期
- `NNN` = 当天序号，从 001 开始
- 确定序号方法：读取 tracker 中已有条目，找到当天已有的最大 NNN，+1。如果当天无条目，从 001 开始。

## Example: Complete tracker after first requirement

After sw-requirements-clarifier writes `REQ-20260526-001`, the tracker should look like:

```yaml
requirements:
  - id: REQ-20260526-001
    title: 用户登录优化
    description: |
      优化现有登录流程，减少用户等待时间，
      增加社交账号登录支持。
    business_domain: general
    priority: P1
    created_at: '2026-05-26'
    updated_at: '2026-05-26'
    current_phase: ideation
    status: active
    phases:
      ideation:
        status: done
        artifacts:
          - paths.artifact_targets.requirement_document
        completed_at: '2026-05-26'
      value_assessment:
        status: pending
        artifacts: []
        completed_at: null
      design:
        status: pending
        artifacts: []
        completed_at: null
      decomposition:
        status: pending
        artifacts: []
        completed_at: null
      execution:
        status: pending
        progress:
          tasks_total: 0
          tasks_done: 0
          worktrees_active: 0
          tasks_blocked: 0
        artifacts: []
        completed_at: null
      merge:
        status: pending
        artifacts: []
        completed_at: null
      test:
        status: pending
        artifacts: []
        completed_at: null
      delivery:
        status: pending
        artifacts: []
        completed_at: null
```
