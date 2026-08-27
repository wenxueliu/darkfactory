---
name: works
description: 按可定制的多步骤流程持续执行开发、测试、审查或修复任务。用户要求使用 /works、从 requirement.md 自动完成 Java 存量项目开发、选择不同流程、为步骤配置 do/check 提示、处理人工反馈、动态选择修复入口或恢复长期任务时使用。
---

# Works

## 参数

- `project_root`：项目根目录，默认使用当前工作目录。该目录应包含 `requirement.md`，也可以包含一个或多个候选子项目。
- `workflow`：流程定义文件，默认使用本 skill 内的 `assets/workflows/development.json`。

用户未明确说明参数时，直接使用上述默认值执行，不询问参数确认；只覆盖用户明确提供的参数，其余参数继续使用默认值。

## 严格执行协议

每次激活都严格按以下顺序执行，不得跳步、合并步骤或凭对话记忆推断当前状态：

1. 将 `project_root` 解析为绝对路径；未提供时使用当前工作目录。
2. 检查 `<project_root>/.works/state.json`。文件不存在时执行 `init`；文件存在时执行 `status`，不得再次初始化或用新的 `workflow` 覆盖已有流程。随后必须调用 `next` 领取一个原子动作。
3. 将 `status` 和最新一次 `next` 返回的 JSON 作为当前事实来源。若 `execution_state=completed`，立即停止并报告完成；若为 `paused` 或 `waiting_for_human`，不得启动业务动作；否则只处理本次 `next_action`。
4. 只读取 `next_action.references_to_read` 列出的参考文件，再执行 `next_action.do`。同一轮不得提前执行后续步骤。若 `next_action.subagent` 非空，必须按其中角色启动 fresh 独立 subagent，等待其完成后再由主 agent 检查产物；不得由主 agent 代做。
5. 严格按 `next_action.check` 收集当前代码版本的新鲜证据。分析或审查使用 `--result/--evidence`；编译和测试使用真实命令。
6. 调用一次 `check` 提交本步骤结果，然后重新调用 `next`。未调用 `check` 不得自行宣布步骤通过或切换步骤。
7. 当 `next_action.type=route` 时，只能从 `allowed_targets` 选择目标，并用 `route` 同时提交非空 reason/evidence、still-valid 和 invalidated。选择最早失效步骤；多个结论仍有效时保留它们。路由后重新调用 `next`，不得沿用旧动作。

只要 `next_action` 存在，就表示流程已确定下一步。立即执行，不询问用户是否继续，不提供跳过当前步骤或直接进入后续步骤的选项。`test_case_design` 必须由 fresh 独立 subagent 在实现前生成 `.works/test-case-design.json`，但不编写或运行测试；功能实现和编译后，`test_generation` 校验并读取该文件、生成测试及 case 映射，`regression_test` 只执行映射选择的最小相关测试。外部依赖与修改无关时忽略，确实涉及时使用 mock、stub 或 fixture 隔离，不得因 Nacos、MySQL、Redis 等服务不可用而停止。

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

初始化后，控制面管理 `.works/state.json`、`events.jsonl`、`goal.json`、`decisions.json`、`inbox/` 和 `artifacts/`。不得绕过 CLI 手工改写这些控制面文件，也不要创建第二套计划或状态。默认流程额外生成 `.works/test-case-design.json` 作为用例设计产物。需求映射、代码定位、复用决策、产物哈希和检查证据由控制面推进。`reuse_analysis` 必须提交可校验的 `reuse_decisions`，后续步骤只能读取该字段决定复用或 fallback。

每次工具调用、子 Agent 返回、check、route 和完成声明前都重新调用 `next`。若返回 `interpret_feedback`，先用 `feedback-respond` 提交理解和 `continue|ask|pause` 决定；硬暂停优先于所有业务动作。消息送达不等于已采纳：delivered、observed、acknowledged 仍需处理，只有 applied 是不再注入和阻断的反馈终态。applied 仅表示反馈已影响计划或执行，不代替步骤 check；后续发现处理不足时追加新反馈或使步骤失效，不回退原反馈状态。

## API 复用协议

默认 Java 流程对每个功能点独立执行以下层级，不得把不同功能点合并判断：

- `T0`：目标类自身已经存在且可直接调用的方法。
- `T1`：同一业务层、同一模块或明确允许依赖模块中的已有公开 Service API。
- `T2`：项目架构明确允许的跨层或跨模块公开端口。Mapper/Repository 只有在目标 Service 本就拥有该聚合的持久化职责时才可作为候选，不能作为找不到 Service API 时的通用捷径。

必须按 `T0 -> T1 -> T2` 串行处理：枚举当前层候选，逐个执行参考资料定义的全部硬门禁；当前层存在通过全部门禁的候选时，选定一个并停止搜索更低优先层。只有当前层候选全部被拒绝，且每个拒绝都有证据时，才能进入下一层。只有 T0、T1、T2 都穷尽且没有合格候选时，才能选择最小新增实现的 fallback。层级接近度只用于通过全部门禁后的排序，不能覆盖语义、依赖方向、事务或副作用约束。

`reuse_analysis` 的 evidence 必须是单个 JSON 对象，顶层只使用 `reuse_decisions` 字段，并严格采用当前 `next_action.check` 给出的 schema。JSON 中以 `current_class`、`same_layer`、`cross_layer` 分别表示 T0、T1、T2；`selected=null` 表示三层候选全部不可行后批准进入最小新增 fallback 分支。不得使用 Markdown 代码围栏、注释、省略号或 JSON 之外的说明。控制面拒绝的 evidence 视为本步骤失败，不能人工宣布通过。

`implementation` 的 evidence 同样必须是单个 JSON 对象，顶层只使用 `implementation_reuse` 字段。每个功能点报告 `invoke` 或 `fallback` 及实际调用/实现位置；控制面会与已持久化的 `reuse_decisions.selected` 比对，不一致时不得通过。

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
- API 复用：每个功能点都有通过控制面校验的 `reuse_decisions`；选择 T1/T2 时已穷尽更高优先层，选择 fallback 时已穷尽 T0/T1/T2。
- 用例设计：每个功能点已映射到待实现后的测试场景、输入、预期结果和边界条件，且未修改测试代码。
- 实现：每个功能点已落到目标存量方法，diff 中没有无关改动，并保留既有调用约定。
- 编译与回归：当前修改版本已有退出码、测试统计和实际选择范围明确的新鲜命令证据。

参考路径相对于本 skill 目录。未被 `next_action.references_to_read` 列出的参考资料不要预加载：

- Java 项目与模块定位：见 [references/java-project-discovery.md](references/java-project-discovery.md)。
- Java 存量开发、API 复用与实现后测试：见 [references/java-brownfield-development.md](references/java-brownfield-development.md)。
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

每个步骤必须有唯一 `id` 和非空 `do/check`；可选 `purpose`、`route_when` 为模型提供路由语义。`next` 声明直接后继，`forward_policy` 支持 `next_only`、`declared` 和低风险流程专用的 `any_defined`；`declared` 通过 `forward_targets` 授权更远前跳。已访问步骤始终可以重新打开，未访问步骤不能仅凭 JSON 顺序成为恢复目标。只有声明 `complete: true` 的当前步骤可选择 `__complete__`。旧 workflow 的 `on_success/on_failure` 仍可加载以便迁移，但新 workflow 应使用动态路由字段。
