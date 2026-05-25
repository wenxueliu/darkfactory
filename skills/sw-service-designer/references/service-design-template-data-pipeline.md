# 数据管道服务设计模板 (Data Pipeline Service Design Template)

## 使用说明

用于数据管道服务 (Spark/Flink/Airflow 等) 的详细设计。

---

# 服务详细设计: {service_id} (data-pipeline)

**设计ID:** `{DESIGN-YYYYMMDD-NNN}-{service_id}`
**关联特性设计:** `designs/{requirement_id}-design.md`
**服务:** `{service_id}` (语言: {language})
**状态:** `draft | reviewed | approved`

## S1. 技术决策

| ID | 决策 | 理由 | 替代方案 | 权衡 |
|----|------|------|---------|------|
| D-{svc}-1 | {处理框架} | {为什么} | {放弃的方案} | {牺牲了什么} |
| D-{svc}-2 | {checkpoint/offset 策略} | {为什么} | {放弃的方案} | {牺牲了什么} |

## S2. 管道架构

```
SOURCE → TRANSFORM → SINK

{source} → {transform_1} → {transform_2} → {sink}
```

### 管道参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 输入源 | {Kafka topic / S3 / DB table} | {说明} |
| 输出目标 | {DB table / S3 / Kafka topic} | {说明} |
| 处理模式 | batch / streaming / micro-batch | {说明} |
| 并行度 | {N} | {说明} |

## S3. 数据 Schema 与转换规则

### 输入 Schema

```yaml
# {input_entity}
fields:
  - name: {field}
    type: {type}
    source: {来自哪个字段}
```

### 输出 Schema

```yaml
# {output_entity}
fields:
  - name: {field}
    type: {type}
    derived_from: {从哪个输入转换}
```

### 转换规则

| 转换步骤 | 输入 | 输出 | 逻辑 | 异常处理 |
|---------|------|------|------|---------|
| validate | raw_data | validated_data | {校验规则} | 写入 DLQ |
| transform | validated_data | enriched_data | {转换逻辑} | 跳过 + 告警 |

## S4. 状态管理

### Checkpoint / Offset 策略

| 策略 | 配置 | 说明 |
|------|------|------|
| Checkpoint 间隔 | {N} 秒 / {M} 条 | {说明} |
| Offset 提交 | at-least-once / exactly-once | {说明} |

### 故障恢复

| 故障类型 | 恢复策略 | 数据丢失风险 |
|---------|---------|------------|
| Task 失败 | 从最近 checkpoint 重启 | {评估} |
| 输入源不可用 | 重试 {N} 次 | {评估} |
| 输出目标不可用 | spillover + 告警 | {评估} |

## S5. 错误处理与重试策略

| 错误类型 | 处理方式 | 重试 | 死信 |
|---------|---------|------|------|
| 数据格式错误 | 跳过 + metrics | 不重试 | DLQ |
| 临时性故障 | 重试 | 指数退避 ×3 | DLQ |
| 业务规则违反 | 跳过 + 告警 | 不重试 | DLQ + 通知 |

## S6. 安全设计

| 关注点 | 方案 |
|--------|------|
| 数据传输加密 | TLS / SSL |
| 敏感字段处理 | 脱敏 / 假名化 |
| 数据访问控制 | IAM role / service account |
| 审计 | 记录每次运行: input_count, output_count, error_count, lag |

## S7. UT 设计 (L1)

加载 `test-case-template.md`。

| 用例 ID | 转换函数 | 场景 | 输入 | 预期输出 |
|---------|---------|------|------|---------|
| UT-{缩写}-001 | `validate{Entity}` | 正常数据 | `{正常 record}` | `Right(validated)` |
| UT-{缩写}-002 | `validate{Entity}` | 格式错误 | `{异常 record}` | `Left(ValidationError)` |

**最少要求:** 每个转换函数 ≥ 2 UT 用例。

## S8. 集成测试设计 (L2)

| 用例 ID | 场景 | 输入数据 | 预期输出 | 预期副作用 |
|---------|------|---------|---------|----------|
| INT-{缩写}-001 | 完整管道 happy | N 条正常记录 | N 条输出到 sink | metrics 正常 |
| INT-{缩写}-002 | 部分错误数据 | M 正常 + K 异常 | M 输出 + K DLQ | error_count = K |
| INT-{缩写}-003 | 输出目标不可用 | N 条 | 管道失败 + spillover | 告警触发 |

**最少要求:** ≥ 3 集成测试用例 (happy + partial_error + sink_unavailable)。
