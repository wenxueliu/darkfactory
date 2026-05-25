# Requirements Tracker Update

## Purpose

此文档定义如何更新 `_context/memory/sw-shared/requirements-tracker.yaml`。sw-requirements-clarifier 是第一个写入者——在完成需求澄清和规格文档后，将需求条目写入 tracker。

## Tracker File Path

```
{project-root}/_context/memory/sw-shared/requirements-tracker.yaml
```

## Operation: Create or Append Requirement Entry

### Step 1: Read the tracker

读取 `_context/memory/sw-shared/requirements-tracker.yaml`。

### Step 2: Determine mode

- **Create mode（首次使用）**: 文件只有模板注释和 `# TODO` 占位行，`requirements:` 列表下无实际条目。
- **Append mode（已有需求）**: `requirements:` 列表下已有至少一个非注释的需求条目。

### Step 3: Build the new entry

从刚完成的需求规格文档中提取字段：

| Tracker 字段 | 数据来源 | 示例值 |
|-------------|---------|--------|
| `id` | 需求规格第 13 行 `需求ID` | `REQ-20260526-001` |
| `title` | 需求规格第 11 行 `需求标题` | `用户登录优化` |
| `description` | 需求规格第 1 节「问题陈述」1-3 句摘要 | 见规格文档 |
| `business_domain` | `_context/config.yaml` → `sw.business_domain` | `general` |
| `priority` | 需求规格第 131 行「综合优先级」 | `P1` |
| `created_at` | 今天日期 `YYYY-MM-DD` | `2026-05-26` |
| `updated_at` | 同上 | `2026-05-26` |
| `current_phase` | `ideation` | `ideation` |
| `status` | 推导（见下方规则） | `active` |

### Step 4: Build phases block

```yaml
phases:
  ideation:
    status: done
    artifacts:
      - _context/memory/sw-shared/requirements/{requirement_id}.md
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
          - _context/memory/sw-shared/requirements/REQ-20260526-001.md
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
