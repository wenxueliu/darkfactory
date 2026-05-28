# 服务类型检测 (Service Type Detection)

## 检测优先级

1. `service-registry.yaml` 中 `services[].type` 显式声明 → 直接使用
2. `service-registry.yaml` 中 `services[].language` 字段 → 按规则推断
3. 无 `service-registry.yaml` (单体模式) → 默认 `backend`

## 语言 → 类型映射

### Backend
匹配: `java-*`, `kotlin-*`, `go-*`, `python-*` (排除 data/airflow/etl), `rust-*`, `scala-*`, `csharp-*`, `php-*`, `ruby-*`
模板: `service-design-template-backend.md`

### Frontend
匹配: `typescript-react`, `typescript-vue`, `typescript-angular`, `typescript-svelte`, `typescript-solid`, `javascript-react`, `javascript-vue`, `javascript-angular`
模板: `service-design-template-frontend.md`

### BFF
匹配: `typescript-next`, `typescript-nest`, `typescript-remix`, `*-bff`, `*-gateway`
模板: `service-design-template-bff.md`

### Data Pipeline
匹配: `python-data`, `python-airflow`, `python-prefect`, `python-dagster`, `java-spark`, `java-flink`, `java-beam`, `scala-spark`, `scala-flink`, `*-etl`, `*-pipeline`
模板: `service-design-template-data-pipeline.md`

## 降级策略

| 场景 | 行为 |
|------|------|
| 无 service-registry.yaml | 默认 `backend` |
| language 不在映射规则中 | 默认 `backend` + 警告 |
| type 为未知值 | 报错，提示有效值: backend/frontend/bff/data-pipeline |
| 自定义模板路径不存在 | 警告 + fallback 到内置模板 |

## 自定义服务类型

在 `_context/config.yaml` 中扩展:
```yaml
sw:
  design_phase:
    service_design_templates:
      ml-model: "service-design-template-ml-model.md"
```
