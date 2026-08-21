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

## Java 存量开发约束

- 逐功能点定位并修改已有类的已有方法；新增辅助类不能代替存量修改。
- 按同类复用、同层复用、跨层复用的顺序搜索，Service 逻辑优先直接调用当前类或已有 Service 方法。
- 真实复用已有 API；不得复制其实现再修改，不得为了省事从 Service 绕到 Mapper。
- 在复用前从声明和既有调用点核对参数、返回值、异常、事务和统一响应约定。
- 保留已有公开方法签名、既有调用方语义和项目分层/代码风格。
- 编译失败或回归失败时依据 `.works/state.json` 的 `last_check` 修复并重新执行编译和测试，禁止跳过或削弱测试。

## 跨平台构建

优先使用仓库 Wrapper。根据运行环境直接选择现有文件：

- Linux/macOS：`./mvnw`、`./gradlew`，或已安装的 `mvn`、`gradle`。
- Windows：`mvnw.cmd`、`gradlew.bat`，或已安装的 `mvn`、`gradle`。

使用正斜杠描述路径，检查文件是否存在后再选择命令；不要假设文件系统区分大小写，不要把 Bash 或 PowerShell 专属语法写入工作流。

## 流程语义

每个步骤必须有唯一 `id` 和非空 `do/check`，所有跳转目标必须存在。检查成功进入 `on_success`，值为 `null` 时完成；检查失败先按 `on_failure.retries` 原地重试，超过次数后进入 `on_failure.goto`。`retries: 0` 表示第一次失败立即跳转。
