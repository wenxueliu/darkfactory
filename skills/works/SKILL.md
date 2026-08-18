---
name: works
description: 仅面向 OpenCode + MiniMax M2.7 的全自动存量 Java/Maven 实现 Skill。用户输入 /works，或要求依据明确的 requirement.md 无人值守完成需求分析、代码实现、TDD 和最终验收时使用。由 works 保持唯一状态和完成判定，可按阶段调用其他 OpenCode Skill 提供方法，但不调用 Agent/subagent 或人工确认。
---

# Works

从明确的 `requirement.md` 一直执行到代码和全部验收通过。不要询问用户，不调用 Agent/subagent，不在中间停下请求确认。按 [Skill routing](references/skill-routing.md) 调用其他 Skill；调用完成后立即返回 works 状态机。

## OpenCode 执行契约

先读取 [OpenCode profile](references/opencode.md)，然后使用 OpenCode 原生 Skill、文件和终端工具。每轮运行：

```bash
python3 <skill-dir>/scripts/works.py --project <project> status
```

只完成返回的结构化 `next_action.id`。它同时给出当前 Req、可用 Skill 和成功证据。动作包含“编辑并运行门禁”时，把两者视为一个不可分割步骤；完成后立即再次运行 `status`。持续执行，直到 `state` 为 `COMPLETE`。命令失败时读取输出、记录发现、改变工作区或策略后重试；CLI 会拒绝完全相同的失败重放。

会话中断或上下文压缩后先运行 `recover`。探索得到可复用事实或关键选择时，用 `note` 写入轻量磁盘记忆；不要建立第二套 task plan。细节见 [Persistent memory](references/persistent-memory.md)。

## 自主流程

1. `doctor`、`init`、`tdd-init`。
2. 选择一个稳定旧测试运行 `probe`，测试命令显式开启测试。
3. `contract-init` 后读取完整 requirement 和仓库，把所有独立行为写入 `requirement-contract.json`；为每个 Req 写可观察验收标准，并给出覆盖全部 Req 的真实验收命令；运行 `contract-check`。
4. `impact-init` 后从仓库填写 `impact-map.json`，运行 `impact-check`。
5. 对 `current_req` 添加一个行为测试并运行 `red`；只接受目标断言失败。
6. 最小实现当前 Req 并运行完全相同命令的 `green`。继续下一 Req，不暂停。
7. 所有 Req Green 后运行一次 `finalize`。它重放全部 TDD 测试、检查 Service 边界，并自动运行契约中的每条验收命令。
8. 若 finalize 失败，诊断受影响 Req，运行 `reopen -- --req <REQ>`。CLI 会追加一个 repair Req；为失败行为建立新的 Red→Green 修复切片，再次 finalize。不要请求人工处理。
9. 只有 `status.state == COMPLETE` 才报告完成。

## 核心命令

```bash
python3 <skill-dir>/scripts/works.py --project . doctor
python3 <skill-dir>/scripts/works.py --project . init
python3 <skill-dir>/scripts/works.py --project <project> recover
python3 <skill-dir>/scripts/works.py --project <project> note -- --kind finding --text "<fact>" [--req <REQ>]
python3 <skill-dir>/scripts/works.py --project <project> note -- --kind decision --text "<choice>" [--req <REQ>]
python3 <skill-dir>/scripts/works.py --project <project> tdd-init
python3 <skill-dir>/scripts/works.py --project <project> probe -- --testcase ExistingTest#behavior -- <maven-command>
python3 <skill-dir>/scripts/works.py --project <project> contract-init
python3 <skill-dir>/scripts/works.py --project <project> contract-check
python3 <skill-dir>/scripts/works.py --project <project> impact-init
python3 <skill-dir>/scripts/works.py --project <project> impact-check
python3 <skill-dir>/scripts/works.py --project <project> red -- --req <REQ> --test-file <file> --testcase <case> -- <maven-command>
python3 <skill-dir>/scripts/works.py --project <project> green -- --req <REQ> -- <same-maven-command>
python3 <skill-dir>/scripts/works.py --project <project> finalize
python3 <skill-dir>/scripts/works.py --project <project> reopen -- --req <REQ>
```

Maven 测试命令必须包含 `-DskipTests=false` 和 `-Dmaven.test.skip=false`，并覆盖 POM 中其他值为 true 的 `skip*test*` 属性。

填写需求契约时读取 [Requirement contract](references/requirement-contract.md)；处理 TDD 证据时读取 [TDD evidence](references/tdd-evidence.md)；分析分层时读取 [Service boundary](references/service-boundary.md)。
