# 文档定义包与分级解析

文档资源由统一解析器按以下优先级查找：

```text
项目级：{project-root}/_context/templates/
用户级：{user-context-root}/templates/
Skill 内置：skills/<owner-skill>/references/document-definitions/
```

优先级从高到低。每个资源单独回退：项目或用户层可以只覆盖模板、门禁或验证器，未声明的资源继续继承下一层。一个完整的解析结果必须有可用模板；门禁和验证器可以缺省，因此覆盖层可以只声明需要替换的资源。

## 定义包目录

```text
templates/{document-type}/{variant}/
├── manifest.yaml
├── template.md       # 必选
├── gate.yaml         # 可选
└── validator.yaml    # 可选
```

当前实现支持的文档类型由调用方传入，例如：

```text
requirements/default
requirements/fintech
service-design/backend
feature-design/default
```

当前内置定义包位置：

| Skill | 文档类型 | 可用 variant |
|---|---|---|
| `sw-requirements-clarifier` | `requirements` | `default`、`fintech`、`ecommerce`、`internal-tools` |
| `sw-feature-designer` | `feature-design` | `default` |
| `sw-service-designer` | `service-design` | `default`、`backend`、`frontend`、`bff`、`data-pipeline` |
| `sw-e2e-designer` | `e2e` | `default` |
| `sw-strategic-planner` | `plan` | `default` |
| `sw-document-project` | `project-overview`、`project-index`、`source-tree`、`deep-dive` | `default` |

这些定义包分别位于对应 Skill 的 `references/document-definitions/` 下。新增 variant 只需新增目录和 manifest，不需要修改解析器。

`variant` 精确匹配失败时，在同一层回退到 `default`，然后才进入下一层。

## manifest.yaml

```yaml
document_type: requirements
variant: fintech
contract: sw.requirements
version: "1.0"

resources:
  template: template.md
  gate: gate.yaml
  validator: validator.yaml
```

资源默认采用 `replace`。显式禁用下层资源：

```yaml
resources:
  gate:
    mode: disabled
```

自定义资源已声明但文件不存在时，解析器会失败，不会静默回退到内置资源。

## 配置用户级上下文

```yaml
sw:
  document_contracts:
    user_context_root: "../shared-harness-context"
```

相对路径相对于项目根目录解析。项目级模板根目录固定为 `_context/templates`；用户级模板根目录为 `{user_context_root}/templates`。

## 解析和验证

```bash
python3 -m document_contracts resolve \
  --document-type requirements \
  --variant fintech \
  --root project=./_context/templates \
  --root user=../shared-harness-context/templates \
  --root skill=./skills/sw-requirements-clarifier/references/document-definitions

python3 -m document_contracts validate \
  --document-type requirements \
  --variant fintech \
  --document ./_context/memory/sw-shared/requirements/REQ-001.md \
  --root project=./_context/templates \
  --root user=../shared-harness-context/templates \
  --root skill=./skills/sw-requirements-clarifier/references/document-definitions
```

模板可以使用稳定的 section ID，避免验证器依赖标题或章节编号：

```markdown
---
document_type: requirements
contract: sw.requirements
contract_version: "1.0"
---

<!-- section-id: acceptance_criteria -->
## 成功标准
```

文档身份元数据和稳定 section ID 都是契约的一部分。没有 section ID 的受结构规则约束的文档不通过验证；标题只是展示文本，不能作为契约字段。

## Python API

```python
from document_contracts import DefinitionResolver, DocumentValidator, ResourceRoot

definition = DefinitionResolver([
    ResourceRoot("project", project_templates),
    ResourceRoot("user", user_templates),
    ResourceRoot("skill", builtin_templates),
]).resolve("requirements", "fintech")

result = DocumentValidator().validate(definition, document_path)
```

解析结果包含每个资源的实际来源，便于诊断模板覆盖和验证规则继承问题。

## 独立运行与组合运行

每个产出 Skill 都可以只使用自己的内置定义包独立生成文档；组合运行时，上游文档通过契约身份和稳定 section ID 被下游消费：

```text
sw.requirements → sw.feature-design → sw.service-design → sw.e2e
        └──────────────────────────────→ sw.plan
```

`sw-grill-docs` 是横向审查消费者，不拥有上述文档的模板；`sw-controller` 只负责编排和汇总，不跨 Skill 读取内部资源。
