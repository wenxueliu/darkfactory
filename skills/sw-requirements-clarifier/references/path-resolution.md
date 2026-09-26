# 需求澄清语义路径解析

`sw-requirements-clarifier` 不把项目的物理目录作为调用契约。调用方可以通过 `paths` 输入覆盖任意默认路径；未覆盖的字段从项目配置或本 Skill 的 `path-defaults.yaml` 获取。

## 优先级

同一字段按以下顺序覆盖，后者优先：

1. Skill 内置 `path-defaults.yaml`
2. `paths` 对应的项目配置（`config_file` 中的 `sw.requirements.paths`）
3. 调用方输入的 `paths`

路径字段独立合并；数组字段在高优先级声明时整体替换，不隐式拼接。所有相对路径都相对于 `project_root` 解析，路径分隔符使用 `/`。

## 输入结构

```yaml
paths:
  config_file: _context/config.yaml
  config_user_file: _context/config.user.yaml
  definition_roots:
    project: _context/templates
    user: null
    skill: skills/sw-requirements-clarifier/references/document-definitions
  evidence:
    context_files: [CONTEXT.md]
    context_maps: [CONTEXT-MAP.md]
    decision_roots: [knowledge/_enterprise/decisions]
    knowledge_roots:
      patterns: knowledge/_enterprise/patterns
      lessons: knowledge/_enterprise/lessons
      contracts: knowledge/_enterprise/contracts
      decisions: knowledge/_enterprise/decisions
  artifact_targets:
    requirement_document: _context/memory/sw-shared/requirements/{requirement_id}.md
    gate_report: _context/memory/sw-shared/requirements/{requirement_id}-gate.md
    value_assessment: _context/memory/sw-shared/value-assessment/{requirement_id}.md
    tracker: _context/memory/sw-shared/requirements-tracker.yaml
    knowledge_root: knowledge
    tasks: _context/memory/sw-shared/tasks.yaml
    reviews: _context/memory/sw-shared/reviews
```

## 边界规则

- `definition_roots` 只负责查找模板、门禁和验证器；项目、用户、Skill 三层资源仍按统一解析器的优先级处理。
- `evidence` 是只读输入；缺失的上下文或知识目录只记录 `NOT_FOUND`，不自动创建、不写入。
- `artifact_targets` 是写入目标，包含跨 Agent 共享的 `tracker`（本 Skill 是它的第一个写入者）；正式写入前必须满足用户确认和对应阶段门禁。
- `knowledge_root` 只用于知识沉淀，不作为需求文档或 tracker 的替代位置。
- 模板中引用的下游任务、评审等路径通过 `artifact_targets.tasks` 和 `artifact_targets.reviews` 获取，不在流程中拼接物理目录。
- `user` 定义根可以由调用方直接提供，也可以由 `config_file` 中的 `sw.document_contracts.user_context_root` 推导为其 `templates` 子目录。
- `paths` 不承载外部 Skill 的内部路径；外部 Skill 不可用时按 `SKIPPED` 协议继续。
