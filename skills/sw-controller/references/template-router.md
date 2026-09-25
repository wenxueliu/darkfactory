# 文档定义路由

模板、门禁和验证器由统一文档定义解析器加载。`sw-controller` 只负责选择文档类型和场景，不直接读取其他 Skill 的模板文件。

## 定义包

每个文档生产 Skill 自己维护内置定义包。完整定义包必须提供模板；项目/用户覆盖层可以只声明需要替换的门禁或验证器，最终结果仍必须解析出模板：

```text
skills/<skill>/references/document-definitions/
└── <document-type>/<variant>/
    ├── manifest.yaml
    ├── template.md       # 必选
    ├── gate.yaml          # 可选
    └── validator.yaml    # 可选
```

项目级和用户级定义包使用同样的目录结构：

```text
{project-root}/_context/templates/<document-type>/<variant>/
{user-context-root}/templates/<document-type>/<variant>/
```

所有相对路径都以当前 `manifest.yaml` 所在目录为基准。

## 场景映射

| 业务场景 | requirements variant | feature-design variant |
|---------|----------------------|------------------------|
| `general` | `default` | `default` |
| `fintech` | `fintech` | `default` |
| `ecommerce` | `ecommerce` | `default` |
| `internal-tools` | `internal-tools` | `default` |
| `java-springboot-enterprise` | `default` | `default` |

服务设计的 variant 由服务类型决定：`backend`、`frontend`、`bff`、`data-pipeline`。

## 解析优先级

调用方按以下顺序传入资源根目录：

```text
project → user → skill
```

每一层先找精确 variant，再找该层的 `default`。`template`、`gate`、`validator` 分别解析；未声明的可选资源继续向下层查找。

已声明但不存在的资源是配置错误，必须失败；不允许静默切换到低优先级资源。

## 统一入口

```bash
python3 -m document_contracts resolve \
  --document-type requirements \
  --variant fintech \
  --root project=./_context/templates \
  --root user=../shared-harness-context/templates \
  --root skill=./skills/sw-requirements-clarifier/references/document-definitions
```

解析结果必须包含：

- `document_type`
- `variant`
- `contract`
- `version`
- 每个资源的实际路径和来源层级

## 新增业务场景

新增场景时，在对应 Skill 的内置定义包中新增 variant，不修改 Agent 核心逻辑：

```text
skills/sw-requirements-clarifier/references/document-definitions/
└── requirements/healthcare/
    └── manifest.yaml
```

项目专属场景直接放入项目 `_context/templates`，不需要修改 Skill 文件。
