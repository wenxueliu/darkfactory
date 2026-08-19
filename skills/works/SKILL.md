---
name: works
description: 仅面向 OpenCode + MiniMax M2.7 的全自动存量多模块 Java/Maven 实现 Skill。依据明确 requirement.md 完成需求拆分、按 Req×module DAG/Wave 并行派发 Subagent、先实现再用全新 Mockito 定向测试验证修改代码。数据库必须 mock，不运行未修改部分的测试。Works 保持唯一状态和完成判定。
---

# Works

从明确的 `requirement.md` 一直执行到代码和全部验收通过。不要询问用户，不在中间停下请求确认。按 [Skill routing](references/skill-routing.md) 加载 `impl-validator`（审查门）或读内置 reference；完成后立即返回 works 状态机。

## OpenCode 执行契约

先读取 [OpenCode profile](references/opencode.md)，然后使用 OpenCode 原生 Skill、文件和终端工具。每轮运行：

先选择当前平台的 Python 入口：Windows 使用 `py -3`，Linux 使用 `python3`；若对应命令不存在则使用 `python`。后续命令中的 `<python>` 始终表示这个入口。

```text
<python> <skill-dir>/scripts/works.py --project <project> status
```

只完成返回的结构化 `next_action.id`。它同时给出当前 Req、应加载的 Skill（仅审查门）或应读的 reference、以及成功证据。动作包含“编辑并运行门禁”时，把两者视为一个不可分割步骤；完成后立即再次运行 `status`。持续执行，直到 `state` 为 `COMPLETE`。命令失败时读取输出、记录发现、改变工作区或策略后重试；CLI 会拒绝完全相同的失败重放。

会话中断或上下文压缩后先运行 `recover`。探索得到可复用事实或关键选择时，用 `note` 写入轻量磁盘记忆；不要建立第二套 task plan。细节见 [Persistent memory](references/persistent-memory.md)。

## 自主流程

1. `doctor`、`init`、`baseline-init`。
2. 运行 `probe` 加载并校验 baseline；若项目尚未由 Git 管理，先执行 `git init`、`git add .`和 `git commit -m "init commit"`。此阶段不执行任何测试。
3. `contract-init` 后读取完整 requirement 和仓库，把所有独立行为写入 `requirement-contract.json`；为每个 Req 写可观察验收标准，并给出覆盖全部 Req 的真实验收命令；运行 `contract-check`。
4. 运行 `contract-review-init`，启动一个全新上下文、只读的校验 subagent，并加载 `impl-validator`。它只读取 requirement 和 requirement contract，返回带 `review_payload` 的审查报告；Works 主 agent 仅将该 payload 写入已初始化的 `contract-review.json`，再运行 `contract-review-check`。失败则修订契约并重新审查。
5. `impact-init` 后从仓库填写 `impact-map.json`，运行 `impact-check`。
6. `module-plan-init` 后按 `Req × Maven module` 填写 DAG 和 Wave，运行 `module-plan-check`。
7. 对当前 Wave 的全部任务同时启动独立 worktree Subagent；合并其单一 commit 后写 task result，并运行 `wave-check`。细节见 [Module-parallel execution](references/module-parallel.md)。
8. 所有 Wave 通过后运行 `finalize`。只接受已经由主控制面重放的修改代码定向测试，不运行其他模块或未修改代码测试。
9. 若 Wave 或 finalize 失败，诊断受影响模块任务；修订 DAG 或重新派发该任务，不推进依赖 Wave。
10. finalize 通过后运行 `implementation-review-init`，由另一个全新上下文、只读的 `impl-validator` subagent 对照 requirement、契约、diff 和测试证据返回 `review_payload`；Works 主 agent 将 payload 写入 `implementation-review.json`，再运行 `implementation-review-check`。失败则对受影响 Req 执行 `reopen` 并修复。
11. 只有 `status.state == COMPLETE` 才报告完成。审查细节见 [Independent reviews](references/reviews.md)。

## 核心命令

```text
<python> <skill-dir>/scripts/works.py --project . doctor
<python> <skill-dir>/scripts/works.py --project . init
<python> <skill-dir>/scripts/works.py --project <project> recover
<python> <skill-dir>/scripts/works.py --project <project> note -- --kind finding --text "<fact>" [--req <REQ>]
<python> <skill-dir>/scripts/works.py --project <project> note -- --kind decision --text "<choice>" [--req <REQ>]
<python> <skill-dir>/scripts/works.py --project <project> baseline-init
<python> <skill-dir>/scripts/works.py --project <project> probe
<python> <skill-dir>/scripts/works.py --project <project> contract-init
<python> <skill-dir>/scripts/works.py --project <project> contract-check
<python> <skill-dir>/scripts/works.py --project <project> contract-review-init
<python> <skill-dir>/scripts/works.py --project <project> contract-review-check
<python> <skill-dir>/scripts/works.py --project <project> impact-init
<python> <skill-dir>/scripts/works.py --project <project> impact-check
<python> <skill-dir>/scripts/works.py --project <project> module-plan-init
<python> <skill-dir>/scripts/works.py --project <project> module-plan-check
<python> <skill-dir>/scripts/works.py --project <project> wave-check
<python> <skill-dir>/scripts/works.py --project <project> finalize
<python> <skill-dir>/scripts/works.py --project <project> implementation-review-init
<python> <skill-dir>/scripts/works.py --project <project> implementation-review-check
<python> <skill-dir>/scripts/works.py --project <project> reopen -- --req <REQ>
```

优先使用 discovery 返回的 Maven 入口：Windows 为 `mvnw.cmd`，Linux 为 `./mvnw`，没有 wrapper 时为 `mvn`。Maven 测试命令必须包含 `-DskipTests=false` 和 `-Dmaven.test.skip=false`，并覆盖 POM 中其他值为 true 的 `skip*test*` 属性。

填写需求契约时读取 [Requirement contract](references/requirement-contract.md)；拆分和并行执行时读取 [Module-parallel execution](references/module-parallel.md)；分析分层时读取 [Service boundary](references/service-boundary.md)。
