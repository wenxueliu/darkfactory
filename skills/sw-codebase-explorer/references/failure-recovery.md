# failure-recovery.md — CodeGraph 搜索失败恢复与停止条件

## 何时加载

当 CodeGraph 结果不理想时加载，包括索引不可用、未找到结果、结果太少、结果过多、
结果不相关或关系不完整。

## 1. 先诊断，不要猜测

检查：

1. `project_root` 是否是 CodeGraph 建索引的项目根目录；
2. `codegraph status --json {project_root}` 是否成功且目标 scope 被覆盖；
3. 搜索词是否有拼写、缩写或命名风格问题；
4. 是否把符号问题误当成文件问题，或把调用关系问题误当成普通 `query`；
5. `--limit`、`--depth`、`--filter` 或 `--pattern` 是否截断了结果。

索引缺失、不可读或工具不可用不是普通“无结果”。立即返回 `BLOCKED`，给出原始错误和
让调用方执行 `codegraph init/index/sync` 的 remediation；不在本 Skill 内自动修改索引。

## 2. 无结果恢复

在下一轮并行执行以下 CodeGraph 查询：

1. 放宽关键词，例如 `authenticateUser` → `auth`，`PaymentGateway` → `payment`；
2. 去掉过窄的 `--filter`/`--pattern`，扩大项目 scope；
3. 切换查询类型：`query`、`files`、`callers`、`callees`、`impact`；
4. 增大 `--limit` 或 `--depth`，并记录是否仍有边界截断。

仍无结果时，使用 `files --json` 确认目标路径在索引中；只有调用者明确询问历史时，才
追加 `git log --grep`。不使用 grep/LSP/AST/glob 补全 CodeGraph 缺失。

## 3. 结果过少或过多

| 症状 | 应对 |
|---|---|
| 只有 1–2 个结果 | 对关键节点并行执行 callers、callees、impact，并检查 files 覆盖 |
| 超过 50 个结果 | 收窄 scope、增加 `--kind`、按模块分批 query；不要只展示第一个 |
| 达到 limit | 提高 limit 或分 scope 查询，在 `gaps` 标记可能截断 |
| 达到 depth | 提高 depth 或分层查询，在 `gaps` 标记影响面不完整 |
| 结果不相关 | 回到意图分析，区分符号、文件、调用链和历史问题 |

## 4. 停止条件

可以停止：

- 至少两种 CodeGraph 查询交叉验证了关键发现；
- 已确认索引覆盖、结果边界和所有重要节点/边；
- 结果足以让调用者直接行动。

必须继续：

- 只执行一种图查询；
- 关键路径依赖未验证的调用关系；
- 结果被 limit/depth/scope 截断；
- 输出含相对路径或无法回指查询证据。

最多 3 轮搜索。第三轮后仍无满意结果时，按以下格式如实报告：

```text
<analysis>
**Literal Request**: [字面请求]
**Actual Need**: [实际需求]
**Success Looks Like**: [理想结果]
</analysis>

<results>
<files>
（未找到或未完整验证匹配文件）
</files>

<answer>
CodeGraph 未找到 [目标]，或当前索引无法证明该结论。
</answer>

<evidence>
status: [READY|BLOCKED|COVERAGE_GAP]
queries: [实际执行的查询]
coverage: [scope、limit、depth、索引统计]
</evidence>

<gaps>
[未索引文件、未解析关系、结果截断或工具错误]
</gaps>

<next_steps>
如需继续：先在 {project_root} 执行 codegraph init/index/sync，或提供更具体的符号/范围。
</next_steps>
</results>
```
