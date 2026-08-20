---
name: works
description: 面向 OpenCode + MiniMax M2.7 的全自动存量 Java/Maven 实现 Skill。用户输入 /works，或要求依据明确 requirement.md 无人值守完成实现、定向测试和验收时使用。以轻量磁盘状态恢复长任务，对高风险需求按需启用独立审查。
---

# Works

从明确的 `requirement.md` 持续执行到实现和验收通过。不要询问用户，不等待阶段确认。先读 `references/opencode.md`，再反复运行：

```text
<python> <skill-dir>/scripts/works.py --project <project> status
```

每次只完成 `next_action.id`，随后立即重新运行 `status`。命令失败时根据真实输出改变工作区或策略再重试；CLI 会阻止完全相同的失败重放。恢复会话时先运行 `recover`。`state.json` 是唯一流程状态，不建立第二套计划。

## 流程

1. 运行 `doctor`、`init`、`preflight`。preflight 发现 Maven/Git、保存 dirty baseline 和生产指纹；非 Git 项目使用 fingerprint baseline，禁止自动 `git init`、`git add` 或 commit，不运行测试。
2. 运行 `contract-init`。按 `references/exploration.md` 探索仓库，再依据 `references/requirement-contract.md` 一次性填写 Req、入口、复用决策、测试目标、风险和验收命令，随后运行 `contract-check`。不要启动 contract-author subagent，也不要创建独立 impact-map。
3. 优先复用当前类已有方法，其次同层 Service API；只有新增持久层调用时才在 contract 中提交两级缺失证据。出现 4 个以上 Req，或安全、权限、事务、迁移、兼容、跨模块/跨服务语义时，状态机会要求 fresh 只读 `impl-validator` 审查契约。
4. 最小实现当前 Req，运行 `implement` 冻结生产 checkpoint。随后添加只覆盖该行为的快速测试并运行 `test`。有外部协作者时优先 Mockito；纯逻辑允许普通 JUnit。禁止无必要的 `@SpringBootTest` 和真实外部基础设施。
5. 所有 Req 完成后运行 `finalize`，重放 Req 测试、检查 Service boundary 并执行契约验收命令。失败时 `reopen -- --req <REQ>`，追加 repair Req 后继续。
6. 高风险 contract（持久层/架构例外、4+ Req、安全/权限/事务/迁移/兼容/跨模块/跨服务）通过 fresh 只读 `impl-validator` 做最终审查；普通改动在确定性门禁通过后直接完成。
7. 只有 `status.state == COMPLETE` 才报告完成。

## 核心命令

```text
<python> <skill-dir>/scripts/works.py --project . doctor
<python> <skill-dir>/scripts/works.py --project . init
<python> <skill-dir>/scripts/works.py --project . preflight
<python> <skill-dir>/scripts/works.py --project . recover
<python> <skill-dir>/scripts/works.py --project . contract-init
<python> <skill-dir>/scripts/works.py --project . contract-check
<python> <skill-dir>/scripts/works.py --project . contract-review-init
<python> <skill-dir>/scripts/works.py --project . contract-review-check
<python> <skill-dir>/scripts/works.py --project . implement -- --req <REQ>
<python> <skill-dir>/scripts/works.py --project . test -- --req <REQ> --test-file <file> --testcase <Class#method>
<python> <skill-dir>/scripts/works.py --project . finalize
<python> <skill-dir>/scripts/works.py --project . implementation-review-init
<python> <skill-dir>/scripts/works.py --project . implementation-review-check
<python> <skill-dir>/scripts/works.py --project . reopen -- --req <REQ>
```

Windows 使用 `py -3`，Linux 使用 `python3`，不可用时使用 `python`。Maven 优先使用 discovery 返回的 wrapper。定向测试命令必须覆盖 POM 中为 true 的测试跳过属性，并确保指定 testcase 在新鲜 JUnit XML 中真实执行通过。

按阶段读取：探索见 `references/exploration.md`，契约见 `references/requirement-contract.md`，实现与测试证据见 `references/code-first.md`，风险审查见 `references/reviews.md`，恢复见 `references/persistent-memory.md`。
