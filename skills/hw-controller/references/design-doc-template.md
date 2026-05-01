# 设计文档模板

## 使用说明

此模板在需求门禁 PASS 后使用。基于 `requirements/{requirement_id}.md` 创建。填入后写入 `{project-root}/_bmad/memory/hw-shared/designs/{requirement_id}-design.md`。

设计文档是开发阶段的唯一技术事实源。代码实现必须回溯到设计决策。

---

# 设计文档: {需求标题}

**设计ID:** `{DESIGN-YYYYMMDD-NNN}`
**关联需求:** `{REQ-YYYYMMDD-NNN}`
**状态:** `draft | reviewed | approved | implemented`
**创建时间:** `{timestamp}`

## 1. 设计概述

{2-3 句话描述技术方案的核心思路。一个不熟悉项目的工程师应该在 30 秒内理解方案。}

## 2. 技术决策

| ID | 决策 | 理由 | 替代方案 | 权衡 |
|----|------|------|---------|------|
| D-1 | {选择的技术方案} | {为什么选这个} | {考虑过但放弃的方案} | {牺牲了什么} |
| D-2 | {选择的技术方案} | {为什么选这个} | {考虑过但放弃的方案} | {牺牲了什么} |

## 3. 架构设计

### 3.1 组件图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Component │────▶│   Component │────▶│   Component │
│      A      │     │      B      │     │      C      │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 3.2 数据流

```
INPUT → VALIDATION → BUSINESS LOGIC → PERSISTENCE → OUTPUT
  │         │             │               │           │
  ▼         ▼             ▼               ▼           ▼
[nil?]   [invalid?]   [exception?]    [conflict?]  [encoding?]
```

### 3.3 组件职责

| 组件 | 职责 | 输入 | 输出 | 依赖 |
|------|------|------|------|------|
| {Name} | {一句话职责} | {输入类型} | {输出类型} | {依赖组件} |

## 4. API/接口设计

### 4.1 API 端点

| Method | Path | 请求体 | 响应 | 错误码 |
|--------|------|--------|------|--------|
| POST | /api/v1/{resource} | `{json schema}` | `{json schema}` | 201, 400, 409, 500 |
| GET | /api/v1/{resource}/{id} | — | `{json schema}` | 200, 404, 500 |

### 4.2 数据模型

```yaml
# {entity_name}
fields:
  - name: {field}
    type: {type}
    nullable: true/false
    constraints: {validation rules}
    description: {business meaning}
```

## 5. 状态管理

### 5.1 状态机

```
           ┌──────────┐
           │  DRAFT   │
           └────┬─────┘
                │ submit
           ┌────▼─────┐
           │ IN_REVIEW│
           └────┬─────┘
          ┌─────┴─────┐
    approve           reject
   ┌──▼──┐         ┌──▼──┐
   │LIVE │         │DRAFT│
   └─────┘         └─────┘
```

### 5.2 状态转换规则

| 当前状态 | 触发事件 | 目标状态 | 前置条件 | 副作用 |
|---------|---------|---------|---------|--------|
| DRAFT | submit | IN_REVIEW | 所有必填字段完整 | 发送通知 |
| IN_REVIEW | approve | LIVE | reviewer 批准 | 写入审计日志 |

## 6. 错误处理策略

| 错误场景 | 异常类型 | HTTP 状态码 | 用户消息 | 重试策略 | 日志级别 |
|---------|---------|------------|---------|---------|---------|
| 资源不存在 | ResourceNotFound | 404 | "未找到 {resource}" | 不重试 | WARN |
| 并发冲突 | OptimisticLockException | 409 | "数据已被修改，请刷新重试" | 用户手动重试 | WARN |
| 上游超时 | UpstreamTimeout | 503 | "服务暂时不可用" | 指数退避 ×3 | ERROR |

## 7. 安全设计

| 关注点 | 方案 | 验证方式 |
|--------|------|---------|
| 认证 | {方案描述} | {测试方式} |
| 授权 | {方案描述} | {测试方式} |
| 输入校验 | {方案描述} | {测试方式} |
| 数据保护 | {方案描述} | {测试方式} |
| 审计日志 | {方案描述} | {测试方式} |

## 8. 测试策略

| 测试层次 | 覆盖目标 | 工具 | 预估用例数 |
|---------|---------|------|-----------|
| 单元测试 | 核心业务逻辑 100% | {框架} | ~{N} |
| 集成测试 | API 端点 + DB 交互 | {框架} | ~{N} |
| E2E 测试 | 关键用户旅程 | {框架} | ~{N} |

## 9. 部署注意事项

- **迁移:** {是否需要数据库迁移，是否向后兼容}
- **特性开关:** {是否需要 feature flag}
- **回滚方案:** {如何回滚，预估回滚时间}
- **监控指标:** {新增哪些监控/告警}

## 10. 开放问题

- {在实现前需要澄清的技术不确定性}
- {设计评审中未达成共识的决策}

## 11. 下游引用

- 需求规格: `requirements/{requirement_id}.md`
- 任务拆分: `_bmad/memory/hw-shared/tasks.yaml`
- 知识库: `_bmad/memory/hw-shared/knowledge-base/decisions/`
