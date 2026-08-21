---
name: works
description: 按可定制的多步骤流程持续执行开发、测试、审查或修复任务。用户要求使用 /works、从 requirement.md 自动完成 Java 存量项目开发、选择不同流程、为步骤配置 do/check 提示、失败重试或成功/失败跳转时使用。默认流程会自动定位 Java 项目、优先复用已有 Service API、修改存量方法并持续到编译和回归测试通过。运行时只维护一个 state.json。
---

# Works

## 初始化

将 `--project` 指向包含 `requirement.md` 的根目录。该目录可以就是 Java 项目，也可以包含一个或多个候选子项目（如 `mall-swarm/`）：

```text
python <skill-dir>/scripts/works.py --project <project-root> init
python <skill-dir>/scripts/works.py --project <project-root> init --workflow <workflow.json>
```

不传 `--workflow` 时使用 `assets/workflows/development.json`。默认流程仅支持 Java 项目，会从根目录向下识别 Maven、Gradle、Wrapper、`src/main/java` 及多模块声明，不依赖固定项目目录名。

初始化后，完整流程定义写入 `.works/state.json`。它是唯一运行时状态；不要创建第二套计划、日志、清单或证据文件。需求映射、代码定位、复用决策和检查证据均通过当前步骤的工作上下文与 `check` evidence 推进。

## 按需读取参考资料

每次执行步骤前，读取响应中 `next_action.references_to_read` 列出的文件；未列出的参考资料不要预加载。路径相对于本 skill 目录：

- Java 项目与模块定位：见 [references/java-project-discovery.md](references/java-project-discovery.md)。
- Java 存量开发、API 复用与测试先行：见 [references/java-brownfield-development.md](references/java-brownfield-development.md)。
- Maven/Gradle 编译和相关测试命令：见 [references/build-and-test.md](references/build-and-test.md)。

自定义 workflow 可在步骤中声明 `references` 字符串数组。每项必须是本 skill 内的正斜杠相对路径，不得引用其他 skill 或平台专属目录。

## 连续执行

初始化后持续循环，直到响应中 `completed` 为 `true`：

1. 执行响应中 `next_action.do` 的全部工作。
2. 按 `next_action.check` 收集可复核证据并提交检查。
3. 立即执行响应刷新后的下一步，不等待阶段确认。
4. 仅在中断恢复时运行 `status`；不要用 `status` 代替推进流程。

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
