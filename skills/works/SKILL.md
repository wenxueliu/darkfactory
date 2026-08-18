---
name: works
description: >
  仅面向 MiniMax M2.7 的存量 Java/Maven 代码安全修改 skill。用户输入 /works，或要求依据
  requirement.md 修改既有 Maven 项目、复用 Service API、保护未提交改动并完成测试验证时使用。
  通过单一 works CLI、state.json 状态机和不可变 Red→Green 证据推进。
---

# Works

## 一个入口，一个状态

所有操作通过 `python3 <works>/scripts/works.py` 执行。`.planning/works-*/state.json` 是唯一流程状态；`evidence/` 保存不可变事实。Markdown 不参与门禁。

每轮先运行：

```bash
python3 <works>/scripts/works.py --project <project> status
```

只执行返回的第一个 `allowed_actions`，绝不执行 `forbidden_actions`。

## 状态机

| 状态 | 动作 | 生产代码可写 |
|---|---|---:|
| `SETUP_REQUIRED` | `tdd-init`，然后用稳定旧测试执行 `probe` | 否 |
| `IMPACT_REQUIRED` | `set-reqs`、`impact-init`、填写影响图、`impact-check` | 否 |
| `READY_FOR_RED` | 只写当前 Req 的一个行为测试，然后 `red` | 否 |
| `READY_FOR_IMPLEMENTATION` | 最小修改当前 Req 的生产代码，然后 `green` | 是 |
| `READY_FOR_ACCEPTANCE` | `verify`，再运行必要的 `accept` 命令 | 否 |
| `COMPLETE` | 审计 diff 和证据后报告 | 否 |
| `BLOCKED` | 读取证据与错误码，不伪造状态 | 否 |

## 开始

```bash
python3 <works>/scripts/works.py --project . doctor
python3 <works>/scripts/works.py --project . init
python3 <works>/scripts/works.py --project <project> tdd-init
python3 <works>/scripts/works.py --project <project> probe -- --testcase ExistingTest#behavior -- <maven command>
```

测试命令必须包含 `-DskipTests=false -Dmaven.test.skip=false`，并覆盖 POM 中所有 true-valued `skip*test*` 属性。

## 影响分析

```bash
python3 <works>/scripts/works.py --project <project> set-reqs --req REQ-1 --req REQ-2
python3 <works>/scripts/works.py --project <project> impact-init
# 填写 <plan>/impact-map.json
python3 <works>/scripts/works.py --project <project> impact-check
```

影响图必须为每个 Req 提供行为、入口、Service API、持久层、测试 seam、风险和真实文件证据。无 Service API 时必须记录有证据的架构例外。

## TDD 循环

```bash
python3 <works>/scripts/works.py --project <project> red -- --req REQ-1 --test-file <file> --testcase <case> -- <maven command>
python3 <works>/scripts/works.py --project <project> green -- --req REQ-1 -- <完全相同的 maven command>
```

- Red 必须是目标 testcase 的 assertion failure；编译、fixture、依赖和环境错误无效。
- Red 前生产指纹必须等于 baseline/上一 Green checkpoint。
- Green 不能修改 Red 测试正文或选择器。
- Green 时执行 Service boundary：入口优先复用或扩展 Service，禁止新增 Mapper/Repository 直连。
- 一个 Green 完成后重新运行 `status`，自动转向下一 Req。

## 验收

```bash
python3 <works>/scripts/works.py --project <project> verify -- --req REQ-1 --req REQ-2
python3 <works>/scripts/works.py --project <project> accept -- --name module-tests -- <真实验收命令>
```

只有 TDD verify 通过，且每个最新命名验收命令退出码为 0，状态才是 `COMPLETE`。

## 安全规则

- 用户已有改动属于 baseline，不覆盖、回滚、格式化或顺手修复。
- 不用删测试、弱化断言、`@Disabled`、跳过模块或伪造 JSON 推进。
- 路径、构建入口、测试 seam 和实现细节先从仓库取证；只有互斥业务语义、权限扩张或不可逆操作才询问用户。
- 不执行 commit、push、发布或不可逆操作，除非用户明确授权。
- 只把真实运行且退出码符合预期的命令称为通过。

证据细节见 [TDD evidence](references/tdd-evidence.md)，状态结构见 [State contract](references/plan-contract.md)，分层规则见 [Service boundary](references/service-boundary.md)。交接时读取 [Handoff](references/handoff.md)。
