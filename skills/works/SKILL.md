---
name: works
description: 仅面向 OpenCode + MiniMax M2.7 的全自动存量 Java/Maven 实现 Skill。用户输入 /works，或要求依据明确的 requirement.md 无人值守完成需求分析、先实现代码、再测试和最终验收时使用。由 works 保持唯一状态和完成判定，可按阶段调用其他 Skill 和 subagent，但不需要人工确认。
---

# Works

从明确的 `requirement.md` 一直执行到代码和全部验收通过。不要询问用户，不在中间停下请求确认。按 `references/skill-routing.md` 加载 `impl-validator`（审查门）或读内置 reference；完成后立即返回 works 状态机。

## OpenCode 执行契约

先读取 `references/opencode.md`，然后使用 OpenCode 原生 Skill、文件和终端工具。每轮运行：

先选择当前平台的 Python 入口：Windows 使用 `py -3`，Linux 使用 `python3`；若对应命令不存在则使用 `python`。后续命令中的 `<python>` 始终表示这个入口。

```text
<python> <skill-dir>/scripts/works.py --project <project> status
```

只完成返回的结构化 `next_action.id`。它同时给出当前 Req、应启动的 fresh subagent、应加载的 Skill（仅审查门）或应读的 reference，以及成功证据。动作包含“subagent payload→写入→运行门禁”时，把它们视为一个不可分割步骤；完成后立即再次运行 `status`。持续执行，直到 `state` 为 `COMPLETE`。命令失败时读取输出、记录发现、改变工作区或策略后重试；CLI 会拒绝完全相同的失败重放。

会话中断或上下文压缩后先运行 `recover`。探索得到可复用事实或关键选择时，用 `note` 写入轻量磁盘记忆；不要建立第二套 task plan。细节见 `references/persistent-memory.md`。

## 自主流程

1. `doctor`、`init`、`baseline-init`。
2. 运行 `probe` 加载并校验 baseline；若项目尚未由 Git 管理，先执行 `git init`、`git add .`和 `git commit -m "init commit"`。此阶段不执行任何测试。
3. `contract-init` 后读取 `references/contract-author.md`，把它作为完整指令交给 OpenCode Task 工具调用 fresh `general` subagent，并同步等待 Task result。该 subagent 充当 contract-author，读取完整 requirement 和仓库，只向父会话返回完整 `contract_payload`；Works 主 agent 收到并校验非空结果后整体写入 `requirement-contract.json`，再运行 `contract-check`。未收到 payload、Task 失败或格式错误都必须启动新的 fresh `general` author，禁止主 Agent代写。
4. 运行 `contract-review-init`，启动一个全新上下文、只读的校验 subagent，并加载 `impl-validator`。它只读取 requirement 和 requirement contract，返回带 `review_payload` 的审查报告；Works 主 agent 仅将该 payload 写入已初始化的 `contract-review.json`，再运行 `contract-review-check`。失败则修订契约并重新审查。
5. `impact-init` 后从仓库填写 `impact-map.json`，运行 `impact-check`。
6. 最小实现当前 Req：先复用当前类已有的等价方法，再考虑同层 Service API，只有都不能满足时才新增对 Mapper/Repository 的调用；运行 `implement` 冻结实现 checkpoint。
7. 只为当前 Req 新实现或修改的行为添加 Mockito 单元测试：禁止 `@SpringBootTest`，第三方和外部依赖直接 mock，不测试或运行无关存量功能。用唯一且精确的 `-Dtest=Class#method` 运行 `test`；实际 testcase 必须匹配该 Req 在契约中声明的 selector（repair Req 回溯原始 Req），且只接受指定 testcase 确实执行并通过。继续下一 Req，不暂停。证据规则见 `references/code-first.md`。
8. 所有 Req 测试通过后运行一次 `finalize`。它重放全部 Req 测试、检查 Service 边界，并自动运行契约中的每条验收命令。
9. 若 finalize 失败，诊断受影响 Req，运行 `reopen -- --req <REQ>`。CLI 会追加一个 repair Req；重新执行实现 checkpoint→测试修复切片，再次 finalize。
10. finalize 通过后运行 `implementation-review-init`，由另一个全新上下文、只读的 `impl-validator` subagent 对照 requirement、契约、diff 和测试证据返回 `review_payload`；Works 主 agent 将 payload 写入 `implementation-review.json`，再运行 `implementation-review-check`。失败则对受影响 Req 执行 `reopen` 并修复。
11. 只有 `status.state == COMPLETE` 才报告完成。审查细节见 `references/reviews.md`。

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
<python> <skill-dir>/scripts/works.py --project <project> implement -- --req <REQ>
<python> <skill-dir>/scripts/works.py --project <project> test -- --req <REQ> --test-file <file> --testcase <case> -- <maven-command>
<python> <skill-dir>/scripts/works.py --project <project> finalize
<python> <skill-dir>/scripts/works.py --project <project> implementation-review-init
<python> <skill-dir>/scripts/works.py --project <project> implementation-review-check
<python> <skill-dir>/scripts/works.py --project <project> reopen -- --req <REQ>
```

优先使用 discovery 返回的 Maven 入口：Windows 为 `mvnw.cmd`，Linux 为 `./mvnw`，没有 wrapper 时为 `mvn`。Maven 测试命令必须包含 `-DskipTests=false`、`-Dmaven.test.skip=false` 和唯一的 `-Dtest=Class#method`，并覆盖 POM 中其他值为 true 的 `skip*test*` 属性。

填写需求契约时读取 `references/requirement-contract.md`；处理实现后测试证据时读取 `references/code-first.md`；分析分层时读取 `references/service-boundary.md`。
