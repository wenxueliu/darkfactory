# CodeGraph 使用协议

## 何时加载

每次执行 `sw-codebase-explorer` 时加载。本文档定义唯一的代码结构搜索后端、命令映射、状态检查和证据格式。

## 1. 工具边界

`codegraph` 是本 Skill 的必需工具依赖。调用者必须提供已安装且版本不低于
`0.9.9` 的 CLI，或者提供等价的 CodeGraph MCP 工具能力。

本 Skill 只读：

- 可以读取 CodeGraph 查询结果和索引状态；
- 不得自动执行 `codegraph init`、`codegraph index`、`codegraph sync` 或
  `codegraph uninit`；
- 索引准备和同步由 setup、项目维护者或调用方负责；
- 不得使用 grep、LSP、AST、glob 或其他本地搜索结果冒充 CodeGraph 证据。

## 2. 调用顺序

1. 将 `project_root` 解析为绝对路径；`scope` 只能用于收敛查询路径或文件过滤。
2. 执行：

   ```text
   codegraph status --json {project_root}
   ```

3. 检查命令是否成功、索引是否可读，以及目标 scope 是否被索引覆盖。保留
   CodeGraph 返回的状态和统计信息，不自行推断新鲜度。
4. 状态通过后，根据 [search-patterns.md](search-patterns.md) 选择查询组合，并
   并行执行至少三个相互独立的查询（若问题本身只需要单一查询则说明原因）。
5. 将查询结果中的节点、边、文件、行号和查询命令映射到结构化输出；路径统一转为绝对路径。

索引缺失、不可读、scope 未覆盖，或 CLI 返回错误时，停止查询并返回：

```text
status: BLOCKED
reason: {CodeGraph 原始错误或覆盖缺口}
remediation: 在 {project_root} 执行 codegraph init/index/sync 后重新运行
```

不要在本 Skill 内自动修复，因为修复会改变项目的 `.codegraph/` 状态。

## 3. 命令映射

| 需要回答的问题 | CodeGraph 查询 |
|---|---|
| 符号定义、符号匹配 | `codegraph query --json --path {root} {search}` |
| 文件树、模块边界、测试文件 | `codegraph files --json --path {root} --format flat`，必要时加 `--filter` 或 `--pattern` |
| 谁调用某符号 | `codegraph callers --json --path {root} {symbol}` |
| 某符号调用了什么 | `codegraph callees --json --path {root} {symbol}` |
| 修改某符号的影响面 | `codegraph impact --json --path {root} {symbol}` |
| 变更文件影响哪些测试 | `codegraph affected --json --path {root} {files...}` |

`query` 的 `--kind`、`--limit`，以及其他命令的 `--depth`、`--filter`、
`--pattern` 只用于控制范围，不得用过小的 limit 代替完整搜索。达到 limit 时必须在
`gaps` 中说明结果可能被截断。

历史问题（提交、作者、引入时间）可以单独使用 git，但必须在 evidence 中标记为
`source: git`；所有当前代码结构、依赖和调用关系仍须来自 CodeGraph。

## 4. 证据记录

每次结果至少记录：

```yaml
codegraph:
  status: READY
  version: "0.9.9"
  project_root: /absolute/project/root
  queries:
    - command: codegraph query --json ...
      purpose: locate symbol definition
      result_count: 2
      truncated: false
  nodes:
    - kind: function
      name: example
      path: /absolute/project/root/src/example.py
      line: 42
  edges:
    - kind: calls
      source: /absolute/project/root/src/a.py:10
      target: /absolute/project/root/src/b.py:42
  gaps: []
```

不得补写 CodeGraph 未返回的节点、边、行号或关系。无法确定的内容写入
`gaps`，并在 `answer` 中明确说明。

## 5. MCP 等价调用

当宿主提供 CodeGraph MCP 而不是 CLI 时，使用同一语义：先执行 status，再执行
query/files/callers/callees/impact/affected 对应操作。输出仍需包含上述
`codegraph.status`、`queries`、节点/边证据和缺口；不能因为传输方式不同而省略证据。
