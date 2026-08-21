---
name: works
description: 按可定制的多步骤流程持续执行开发、测试、审查或修复任务。用户要求使用 /works、从 requirement.md 自动完成 Java 存量项目开发、选择不同流程、为步骤配置 do/check 提示、失败重试或成功/失败跳转时使用。默认流程会自动定位 Java 项目、优先复用已有 Service API、修改存量方法并持续到编译和回归测试通过。运行时只维护一个 state.json。
---

# Works

## 参数

- `project_root`：项目根目录，默认使用当前工作目录。该目录应包含 `requirement.md`，也可以包含一个或多个候选子项目。
- `workflow`：流程定义文件，默认使用本 skill 内的 `assets/workflows/development.json`。

## 严格执行协议

每次激活都严格按以下顺序执行，不得跳步、合并步骤或凭对话记忆推断当前状态：

1. 将 `project_root` 解析为绝对路径；未提供时使用当前工作目录。
2. 检查 `<project_root>/.works/state.json`。文件不存在时执行 `init`；文件存在时执行 `status`，不得再次初始化或用新的 `workflow` 覆盖已有流程。
3. 将本次命令返回的 JSON 作为当前状态的唯一事实来源。若 `completed` 为 `true`，立即停止并报告完成；否则只处理本次返回的 `next_action`。
4. 只读取 `next_action.references_to_read` 列出的参考文件，再执行 `next_action.do`。同一轮不得提前执行后续步骤。
5. 严格按 `next_action.check` 收集当前代码版本的新鲜证据。分析或审查使用 `--result/--evidence`；编译和测试使用真实命令。
6. 调用一次 `check` 提交本步骤结果，并立即解析它返回的新 JSON。未调用 `check` 不得自行宣布步骤通过或切换步骤。
7. 若新响应未完成，从第 3 步继续；不得沿用上一次响应中的 `next_action`。检查失败时服从响应给出的重试或跳转结果，不自行选择状态。

首次初始化命令：

```text
python <skill-dir>/scripts/works.py --project <project_root> init --workflow <workflow>
```

使用全部默认参数时：

```text
python <skill-dir>/scripts/works.py --project . init
```

恢复已有流程时：

```text
python <skill-dir>/scripts/works.py --project <project_root> status
```

默认流程仅支持 Java 项目，会从根目录向下识别 Maven、Gradle、Wrapper、`src/main/java` 及多模块声明，不依赖固定项目目录名。

初始化后，完整流程定义写入 `.works/state.json`。它是唯一运行时状态；不要创建第二套计划、日志、清单或证据文件。需求映射、代码定位、复用决策和检查证据均通过当前步骤的工作上下文与 `check` evidence 推进。

## 上下文与搜索预算

采用“先定位、后局部读取、满足证据即停止”的顺序，避免把整个仓库装入上下文：

1. 首先读取 `requirement.md`、目标目录适用的 `AGENTS.md`/`CLAUDE.md`、构建描述文件，以及 `next_action.references_to_read` 指定的文件。
2. 使用文件名、类名、方法名和调用符号进行精确搜索；先看匹配列表与相关行，再读取命中位置附近的必要区段。
3. 从命中位置只向外扩展一层：声明、直接调用方、直接实现类、最近的测试和相关配置。证据不足时才开启下一轮更窄的搜索。
4. 每轮默认最多完整读取 10 个候选文件或累计 2000 行代码，搜索结果最多保留 100 个匹配。达到预算仍缺证据时，先压缩已确认事实与缺口，再开始下一轮；不要创建额外状态文件。
5. 排除 `.git`、`.works`、`target`、`build`、生成代码、依赖缓存、压缩包和二进制文件。不要递归输出完整目录或读取无关模块。

达到当前步骤的停止条件后立即停止搜索并执行检查：

- 需求：每个功能点都有约束和可验证验收条件。
- 项目定位：已确定构建入口、受影响模块、已有类/方法、直接调用方或最近测试，以及潜在回归面。
- API 复用：已找到候选 API 的声明与既有调用证据，或已记录足以证明无可复用 API 的搜索范围。
- 单元测试：每个功能点已映射到具体测试，且真实命令产生目标行为导致的有效红灯。
- 实现：每个功能点已落到目标存量方法，diff 中没有无关改动，并保留既有调用约定。
- 编译与回归：当前修改版本已有退出码、测试统计和实际选择范围明确的新鲜命令证据。

参考路径相对于本 skill 目录。未被 `next_action.references_to_read` 列出的参考资料不要预加载：

- Java 项目与模块定位：见 [references/java-project-discovery.md](references/java-project-discovery.md)。
- Java 存量开发、API 复用与测试先行：见 [references/java-brownfield-development.md](references/java-brownfield-development.md)。
- Maven/Gradle 编译和相关测试命令：见 [references/build-and-test.md](references/build-and-test.md)。

自定义 workflow 可在步骤中声明 `references` 字符串数组。每项必须是本 skill 内的正斜杠相对路径，不得引用其他 skill 或平台专属目录。

`requirement.md` 明确时不得询问用户确认需求分析、代码位置、复用方案或实现阶段。只有文件缺失、需求自相矛盾、缺少会改变外部行为的关键选择，或需要额外权限时才停止并报告精确阻塞点。

无法用命令表达的分析和审查必须附具体证据：

```text
python <skill-dir>/scripts/works.py --project <project-root> check --result passed --evidence "逐项定位或审查证据"
python <skill-dir>/scripts/works.py --project <project-root> check --result failed --evidence "未满足项与原因"
```

编译和测试必须运行真实命令，不得人工声明通过：

```text
python <skill-dir>/scripts/works.py --project <project-root> check -- <program> <arg1> <arg2>
```

命令由参数列表直接执行，因此不要加入 `cd`、管道、`&&`、通配符或其他 shell 语法。命令工作目录始终为 `<project-root>`；若 Java 项目位于子目录，使用构建工具的项目文件参数或项目支持的等价参数定位它。

## 流程语义

每个步骤必须有唯一 `id` 和非空 `do/check`；可选 `references` 必须是不含空值和重复项的字符串数组。所有跳转目标必须存在。检查成功进入 `on_success`，值为 `null` 时完成；检查失败先按 `on_failure.retries` 原地重试，超过次数后进入 `on_failure.goto`。`retries: 0` 表示第一次失败立即跳转。
