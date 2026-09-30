# search-patterns.md — CodeGraph 查询选择与搜索策略

## 何时加载

每次被调用时加载，用于确定针对当前搜索任务的最佳 CodeGraph 查询组合。

## 1. 决策流程

```text
收到搜索请求
  │
  ├─ 执行 codegraph status --json {project_root}
  │   ├─ 不可用/未建索引 → BLOCKED，不执行 fallback
  │   └─ READY → 继续选择查询
  │
  ├─ 目标明确吗？
  │   ├─ YES → 选择对应 CodeGraph 查询
  │   └─ NO  → files + query + 关系查询并行覆盖
  │
  └─ 是否需要历史上下文？
      ├─ YES → CodeGraph 查询 + git log/blame
      └─ NO  → 只执行 CodeGraph 查询
```

状态检查通过后，首轮默认并行执行至少三种相互独立的 CodeGraph 查询；查询本身只有
一个可验证来源时，必须在 `evidence` 中解释例外。

## 2. 查询类型

### 2.1 `query` — 符号搜索

适用于代码理解、符号定位、定义和名称匹配：

```text
codegraph query --json --path {project_root} --limit {n} {search}
codegraph query --json --path {project_root} --kind function {search}
```

关键符号应与 `callers`、`callees` 或 `impact` 配对。名称不确定时扩大 search 和
limit，不使用其他搜索后端替代。

### 2.2 `files` — 文件结构搜索

适用于文件树、模块边界、文件语言和索引统计：

```text
codegraph files --json --path {project_root} --format flat
codegraph files --json --path {project_root} --filter {scope}
codegraph files --json --path {project_root} --pattern '**/*test*'
```

文件树不等于源码内容；需要符号关系时必须继续执行图查询。

### 2.3 `callers` / `callees` / `impact` — 关系搜索

适用于跨文件调用关系和变更影响：

| 用途 | 命令 |
|---|---|
| 查找调用者 | `codegraph callers --json --path {root} {symbol}` |
| 查找被调用者 | `codegraph callees --json --path {root} {symbol}` |
| 分析符号影响 | `codegraph impact --json --path {root} --depth {n} {symbol}` |
| 分析变更测试 | `codegraph affected --json --path {root} {files...}` |

关系查询必须和定义查询配对，避免把同名符号误判为同一节点。影响分析使用足够的
`--depth`，不能将默认深度当成完整影响面；达到 `--limit` 或深度边界时记录 gap。

### 2.4 git — 历史搜索

只有调用者明确询问提交历史、作者或演化过程时才使用 git：

```text
git log --oneline -- {absolute_path}
git blame {absolute_path}
git log --grep='{pattern}'
```

当前代码结构、依赖和调用关系仍必须来自 CodeGraph；历史结论在 evidence 中标记
`source: git`。

## 3. 并行策略

### 3.1 “在哪里定义/实现”

```text
query       # 符号匹配
files       # 候选目录和文件
callers/callees  # 关系交叉验证
```

### 3.2 “哪些文件包含/使用”

```text
query       # 候选符号
callers/callees  # 调用关系
files       # 完整文件范围
```

### 3.3 “理解代码库结构或影响面”

```text
files       # 文件结构
query       # 符号统计
impact/affected  # 下游依赖与测试边界
```

独立查询必须并行执行；只有后一查询确实依赖前一查询返回的具体符号时才允许串行。

## 4. 停止条件

可以停止：

- 关键发现通过至少两种 CodeGraph 查询交叉验证；
- 已找到所有相关节点、边和文件，且没有 limit/depth 截断；
- 结果足以让调用者行动，无需追问。

必须继续：

- 只执行了一种查询且请求需要关系或覆盖验证；
- 结果达到 limit/depth 上限；
- 路径不是绝对路径；
- 只回答了字面问题，尚未解释调用链或影响。

最多执行 3 轮搜索。第三轮后仍不完整时如实报告 CodeGraph 状态、查询范围、索引覆盖
和剩余 gap，不得用本地搜索结果填充缺失证据。
