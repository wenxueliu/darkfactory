# 配置参考 (Configuration)

> **初次接触？** 先看 [README.md](../README.md) 和 [quickstart.md](quickstart.md)。本文是黑灯工厂所有可配置项的完整参考，覆盖 Config YAML、业务领域模板和场景示例。

---

## 配置项总表

以下配置项在 `_context/config.yaml` 和 `_context/config.user.yaml` 中设置：

| Key | Default | Description |
|-----|---------|-------------|
| `worktree_base` | `{project-root}/.worktree` | Worktree 目录位置 |
| `min_iteration_before_human` | 3 | AI 自主迭代几次后升级到人工 |
| `enabled_reviewers` | `security,logic,performance` | 启用的审查类型 |
| `knowledge_base_auto_update` | `true` | 开发完成后自动更新知识库 |
| `merge_strategy` | `merge` | Worktree 合并策略 |
| `document_output_language` | `Chinese` | Agent 通信和文档输出语言 |
| `communication_language` | `Chinese` | Human-Agent 交互语言 |
| `supported_languages` | `*` (auto-detect) | 目标编程语言列表，`*` 表示自动检测 |
| `business_domain` | `general` | 业务领域标记，驱动模板选择 + Reviewer 策略 + 门禁严格度。支持: `general`, `fintech`, `ecommerce`, `internal-tools`, `java-springboot-enterprise` |
| `kb.freshness.confidence_decay.observed` | 60 | observed 来源衰减：每 N 天 -1 confidence |
| `kb.freshness.confidence_decay.inferred` | 30 | inferred 来源衰减：每 N 天 -1 confidence |
| `kb.freshness.confidence_decay.cross-model` | 30 | cross-model 来源衰减：每 N 天 -1 confidence |
| `kb.freshness.confidence_decay.user-stated` | 0 | user-stated 不衰减（人类知识稳定） |
| `kb.freshness.stale_threshold_days` | 90 | 超过此天数 + effective confidence ≤5 即标记 stale |
| `kb.freshness.auto_expire_days` | 365 | 超过此天数标记为 expired，触发审查 |
| `custom_templates` | (空) | 可选。覆盖内置模板的自定义路径，优先级高于 business_domain |

---

## 业务领域模板

不同业务领域使用不同的需求模板。通过 `business_domain` 配置自动切换：

| business_domain | 需求模板 | 特点 |
|-----------------|---------|------|
| `general` | `requirements-spec-template.md` | 通用 10 章节，适用大多数场景 |
| `fintech` | `requirements-spec-template-fintech.md` | 增加合规/监管/审计追踪/交易一致性/SLA 章节 |
| `ecommerce` | `requirements-spec-template-ecommerce.md` | 增加用户旅程/转化指标/支付结算/A/B 测试/库存状态机 |
| `internal-tools` | `requirements-spec-template-internal-tools.md` | 简化版，减少 ceremony，专注集成点和运维手册 |

**新增业务领域：** 创建 `requirements-spec-template-{domain}.md` → 在 `template-router.md` 添加一行映射 → 提交 PR。Agent 核心逻辑零改动。

**完全自定义模板：** 在 `_context/config.yaml` 中指定 `custom_templates.requirements` 路径，覆盖内置模板。

---

## 业务场景适配示例

### 金融 API 服务

```yaml
# _context/config.yaml
sw:
  enabled_reviewers: "security,logic,performance"  # 全开
  business_domain: "fintech"
  knowledge_base_auto_update: true
  min_iteration_before_human: 2  # 关键项目加强人工介入

# _context/config.user.yaml — 日文团队
communication_language: Japanese
user_name: Tanaka
```

### 内部工具脚本

```yaml
# _context/config.yaml
sw:
  enabled_reviewers: "logic"  # 仅逻辑审查
  business_domain: "internal-tools"
  knowledge_base_auto_update: false
  min_iteration_before_human: 5  # 减少打断
```

---

---

## 需求跟踪器 (Requirements Tracker)

需求全生命周期跟踪由 `_context/memory/sw-shared/requirements-tracker.yaml` 实现。该文件**不是配置文件**，而是各阶段 Agent 自动写入的共享状态文件——sw-controller 将其作为阶段转换检查的权威数据源。

### 文件结构

```yaml
requirements:
  - id: REQ-YYYYMMDD-NNN
    title: 需求标题
    priority: P1
    current_phase: execution
    status: active
    phases:
      ideation:           { status: done, artifacts: [...], completed_at: '...' }
      value_assessment:   { status: done, artifacts: [...], completed_at: '...' }
      design:             { status: done, artifacts: [...], completed_at: '...' }
      decomposition:      { status: done, artifacts: [...], completed_at: '...' }
      execution:          { status: in_progress, progress: {...}, artifacts: [...] }
      merge:              { status: pending, artifacts: [], completed_at: null }
      test:               { status: pending, artifacts: [], completed_at: null }
      delivery:           { status: pending, artifacts: [], completed_at: null }
```

### 与 harness_framework 的协作

| 层级 | 跟踪文件 | 粒度 | 用途 |
|------|---------|------|------|
| 需求级 | `requirements-tracker.yaml` | 阶段 + 任务计数 | sw-controller 决策、人工查进度 |
| 任务级 | Consul KV `workflows/<req_id>/tasks/` | 每个任务实时状态 | Aggregator 调度、Watchdog 恢复 |
| 仪表盘 | WebAPI `/api/workflows` | 全局实时视图 | DAG 可视化、控制操作 |

### 如何查看进度

```bash
# 查看所有需求的阶段状态（一行一个需求）
grep -A1 '^  - id:' _context/memory/sw-shared/requirements-tracker.yaml

# 查看特定需求的执行进度
# 找 phases.execution.progress 字段

# 查看运行时任务级状态（需 harness_framework 运行中）
curl http://localhost:8080/api/workflows
```

## 下一步

| 我想… | 看这里 |
|-------|--------|
| 了解核心设计理念 | [concepts.md →](concepts.md) |
| 查看系统架构 | [architecture.md →](architecture.md) |
| 了解知识库和 KB 生命周期 | [knowledge-base.md →](knowledge-base.md) |
| 多平台技能开发 | [multi-platform.md →](multi-platform.md) |
