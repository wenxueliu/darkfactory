# 模板路由 (Template Router)

## 概述

黑灯工厂支持通过 `business_domain` 配置实现**业务场景快速适配**。不同业务领域自动加载不同的需求模板、设计模板和门禁规则。一套 Agent 定义，多种业务场景，零代码修改。

## 路由机制

```
_bmad/config.yaml
  business_domain: "{domain}"
         │
         ▼
  template-router.md (本文件)
         │
         ├── 需求阶段 → 加载 {domain} 对应的 requirements-spec-template
         ├── 设计阶段 → 加载 {domain} 对应的 design-doc-template (如有)
         └── 门禁检查 → 加载 {domain} 对应的 gate 规则 (如有)
         │
         ▼
  若 {domain} 无专属模板 → fallback 到 default (通用模板)
```

## 领域映射表

| business_domain | 需求模板 | 设计模板 | 门禁规则 | 说明 |
|-----------------|---------|---------|---------|------|
| `general` (默认) | `requirements-spec-template.md` | `design-doc-template.md` | `requirements-gate.md` + `design-gate.md` | 通用场景 |
| `fintech` | `requirements-spec-template-fintech.md` | `design-doc-template.md` + 合规章节 | `requirements-gate.md` + 合规检查 | 金融/支付/保险 |
| `ecommerce` | `requirements-spec-template-ecommerce.md` | `design-doc-template.md` + 用户旅程 | `requirements-gate.md` + A/B 测试检查 | 电商/交易平台 |
| `internal-tools` | `requirements-spec-template-internal-tools.md` | `design-doc-template.md` (简化) | `requirements-gate.md` (简化) | 内部工具/脚本 |
| `java-springboot-enterprise` | `requirements-spec-template.md` (通用) | `design-doc-template.md` | `requirements-gate.md` + `design-gate.md` | v1 默认领域 |

## 模板加载逻辑

当 hw-controller 进入需求阶段时:

1. **读取 config:** `{project-root}/_bmad/config.yaml` → `hw.business_domain`
2. **查映射表:** 在本文档的领域映射表中查找匹配的模板
3. **加载模板:** 加载对应的 `requirements-spec-template-{domain}.md`
4. **Fallback:** 如果 `{domain}` 不在映射表中 → 加载 `requirements-spec-template.md` (通用)
5. **用户自定义:** 如果 `_bmad/config.yaml` 中指定了 `custom_template_path` → 加载用户自定义模板（优先级最高）

## 用户自定义模板

```yaml
# _bmad/config.yaml
hw:
  business_domain: "fintech"

# 可选：完全自定义模板路径（覆盖内置模板）
# custom_templates:
#   requirements: "./my-templates/our-req-spec.md"
#   design: "./my-templates/our-design.md"
```

如果指定了 `custom_templates`:
1. 优先加载自定义路径
2. 如果自定义文件不存在 → 警告 + fallback 到内置模板
3. 自定义模板应遵循与内置模板相同的章节结构（确保门禁检查兼容）

## 新增业务领域

要新增一个业务领域（如 `healthcare`）:

1. 创建 `requirements-spec-template-healthcare.md`
2. 在本文件的领域映射表中添加一行
3. 提交 PR（模板文件是产品代码，用 `feat:` 前缀）

不需要修改任何 Agent 的 SKILL.md。

## 门禁适配

不同领域的门禁检查强度不同:

| 领域 | 需求门禁 | 设计门禁 | P0 定义 |
|------|---------|---------|--------|
| `fintech` | 全部 G1-G4 + 合规附加检查 | 全部 G1-G4 + 安全强化 | 资金安全 + 合规违规 |
| `ecommerce` | G1-G4 + 用户旅程检查 | G1-G4 + 支付安全 | 支付失败 + 数据丢失 |
| `internal-tools` | G1 + G4 (简化) | G1 + G2 (简化) | 生产数据破坏 |
| `general` | G1-G4 | G1-G4 | 功能不可用 |

门禁强度由 hw-controller 根据 `business_domain` 在门禁检查时动态调整。
