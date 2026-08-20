---
name: works
description: 面向 OpenCode + MiniMax M2.7 的全自动存量 Java/Maven 实现 Skill。用户输入 /works，或要求依据明确 requirement.md 无人值守完成实现、定向测试、失败返工和验收时使用。以轻量磁盘状态恢复长任务，并以确定性门禁判定完成。
---

# Works

从明确的 `requirement.md` 持续执行到实现和验收通过。不要等待阶段确认。先读 `references/opencode.md`，再运行：

```text
<python> <skill-dir>/scripts/works.py --project <project> init
```

每次只完成响应中的 `next_action`，并直接使用动作响应刷新后的 `state/current_req/next_action`；不要在每个成功动作后重复运行 `status`。只有恢复、响应丢失或人工检查时运行 `recover/status`。命令失败时记录真实输出和次数，再由 Agent 诊断或重试；不要维护工作区签名。`state.json` 是唯一流程状态，不建立第二套计划。

## 流程

1. `init` 完成项目发现，随后执行唯一正常环境动作 `preflight`：保存 dirty baseline、生产指纹和 Service boundary，不运行 Maven 编译或测试。`doctor` 仅用于人工排障，不属于正常状态机。
2. 把启动命令时的当前工作目录固定为 `project_root`，用于状态与 requirement；把 Java 路径校验、代码扫描和 Maven 执行的根固定为 `discovery.maven_project`，两者不得混用。按 `references/exploration.md` 探索仓库，再依据 `references/requirement-contract.md` 一次性填写 Req、轻量 requirement 来源、入口、复用决策、测试目标和验收命令，随后运行 `contract-check`。`contract-init` 只是创建契约文件的内部准备动作，不代表业务阶段。不要创建独立 impact-map。
3. 优先复用当前类已有方法，其次同层 Service API；只有新增持久层调用时才在 contract 中提交两级缺失证据。`contract-check` 通过后直接进入实现，不做实现前的独立审查。
4. 最小实现当前 Req，运行 `implement` 冻结生产 checkpoint。随后添加只覆盖该行为的快速测试并运行 `test`。测试若表明生产代码需要修改，执行 `rework -- --req <REQ> --reason production-fix`：保留失败日志、归档旧 implementation evidence，并回到实现；不要创建 repair Req。有外部协作者时优先 Mockito；纯逻辑允许普通 JUnit。
5. 所有 Req 完成后运行 `finalize`，统一重放 contract commands，并校验 checkpoint、evidence hash 与 architecture gate，避免对同一 selector 分层重复验收。finalize 重新打开已完成行为时，才用 `reopen -- --req <REQ>` 创建 repair Req。
6. 确定性门禁全部通过后直接进入 `COMPLETE`，不做风险分类或独立 reviewer 审查。只有 `status.state == COMPLETE` 才报告完成。

## 无人值守决策

- 可安全推断：选择最小、可逆解释，并用 `note --kind decision` 记录。
- 可保守降级：保持现有行为，记录 limitation 与验证范围。
- requirement 自相矛盾、与仓库事实冲突、验收不可观察、方案互斥或缺少必要外部凭据，且穷尽仓库证据仍无法正确实现：进入 `BLOCKED`，记录冲突与已检查证据；无人值守不等于编造缺失信息。

## 核心命令

```text
<python> <skill-dir>/scripts/works.py --project . doctor
<python> <skill-dir>/scripts/works.py --project . init
<python> <skill-dir>/scripts/works.py --project . preflight
<python> <skill-dir>/scripts/works.py --project . recover
<python> <skill-dir>/scripts/works.py --project . contract-init
<python> <skill-dir>/scripts/works.py --project . contract-check
<python> <skill-dir>/scripts/works.py --project . implement -- --req <REQ>
<python> <skill-dir>/scripts/works.py --project . test -- --req <REQ> --test-file <file> --testcase <Class#method>
<python> <skill-dir>/scripts/works.py --project . rework -- --req <REQ> --reason production-fix
<python> <skill-dir>/scripts/works.py --project . finalize
<python> <skill-dir>/scripts/works.py --project . reopen -- --req <REQ>
```

Windows 使用 `py -3`，Linux 使用 `python3`，不可用时使用 `python`。Maven 入口由 discovery 统一解析：优先使用 `M2_HOME/bin/mvn`（Windows 为 `mvn.cmd`），无有效入口时依次回退项目 wrapper 和系统 `mvn`。定向测试命令必须覆盖 POM 中为 true 的测试跳过属性，并确保指定 testcase 在新鲜 JUnit XML 中真实执行通过。

按阶段读取：探索见 `references/exploration.md`，契约见 `references/requirement-contract.md`，实现与测试证据见 `references/code-first.md`，恢复见 `references/persistent-memory.md`。
