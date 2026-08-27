# Works 动态路由目标架构

> 状态：已审核的目标架构。本文描述 Works 后续演进方向，不代表当前控制面已经全部实现。

## 目标

Works 面向失败原因无法预先穷举的 Agent 工作流。模型负责根据证据选择最合适的步骤，控制脚本负责限定可执行路径、保存状态并拒绝非法跳转。

核心原则：

> 模型负责选择最合适的合法路径，脚本负责限制哪些路径具有执行权限。

该设计需要同时满足：

- 不要求 workflow 作者提前枚举全部失败原因。
- 模型不能构造不存在的步骤。
- 模型不能在未授权时跳过质量门禁。
- 简单场景可以走短流程，复杂场景可以走长流程。
- 路由决定具有足够上下文、证据和审计信息。

## 职责边界

### Workflow

Workflow 只使用 do 和 check 定义业务执行协议：

- do：进入步骤后执行什么。
- check：什么结果表示步骤完成，以及需要提交什么证据。

不引入固定的 inputs、outputs 或 produces 业务对象模型。步骤需要生成或读取文件时，直接在 do/check 中声明。

### 模型

模型负责理解检查结果和人工反馈、判断哪些历史结论仍然有效、识别需要重新处理的最早环节，并在合法目标中选择修复入口或正常分支。模型必须同时提交路由理由、仍然有效的步骤和已经失效的步骤。

模型还负责判断人工反馈是否需要暂停等待确认。能够从现有目标、证据和约束中得到明确行动时，模型可以说明理解后继续；涉及人的意图、重大取舍或无法消除的歧义时，模型应请求确认。控制面规定的高风险动作和人工明确发出的暂停命令不交给模型自行放行。

### 控制脚本

控制脚本不理解测试缺陷、实现缺陷、需求复杂度等业务语义，只负责：

- 校验目标步骤已经在 workflow 中定义。
- 计算并返回当前合法目标集合。
- 拒绝未授权的前跳和完成请求。
- 保存访问历史、检查证据和路由决定。
- 根据路由策略执行状态转移。

## 步骤定义

步骤保留 do/check，并增加两个可选的模型上下文字段：

    {
      "id": "implementation",
      "purpose": "实现或修复生产功能",
      "route_when": "生产实现不满足当前有效需求时进入",
      "do": "修改已有代码完成需求",
      "check": "检查功能行为、兼容性和必要证据",
      "next": ["compile"],
      "forward_policy": "next_only"
    }

字段语义：

| 字段 | 用途 |
|---|---|
| id | 唯一步骤标识 |
| purpose | 简短说明步骤代表什么 |
| route_when | 为模型说明何时应进入该步骤 |
| do | 步骤执行协议 |
| check | 步骤完成协议 |
| next | 正常直接后继或分支入口 |
| forward_policy | 控制是否允许选择更远的未访问步骤 |

purpose 和 route_when 只为模型提供路由语义，不是由脚本解释或执行的条件表达式。

## 路由依据

### 不枚举失败原因

失败原因属于开放集合。测试失败可能来自需求、测试设计、测试代码、生产实现、fixture、构建环境或多个问题的组合。Workflow 不应维护不断扩张的原因分类树。

模型改为判断：

> 已完成步骤中，最早从哪个步骤开始，其完成条件不再成立？

示例：

- 需求错误：回到 requirements。
- 测试设计错误：回到 test_case_design。
- 测试生成错误：回到 test_generation。
- 生产实现错误：回到 implementation。
- 所有结果仍有效、只需重新运行：留在 regression_test。

多个步骤同时失效时，选择最早失效的步骤。失败原因保存在 evidence 中，不需要转换成控制脚本预定义的枚举值。

### 正常分支与异常修复

正常分支用于选择尚未执行的合法路径，例如：

    requirements
      ├── 简单需求 → implementation
      └── 复杂需求 → exploration

短流程必须有充分证据。无法证明可以安全走短流程时，默认走长流程。

异常修复用于重新打开已经执行过的环节。目标依据最早失效的完成条件选择，而不是依据预定义原因类型选择。

这里的“返回”不是时间或工作区回滚。过去已经发生的文件修改、工具调用和外部影响不会被假定消失。模型始终基于当前世界状态进行弥补、修复和重新验证；历史步骤只是用于定位需要重新处理的业务环节。

## 合法目标集合

每次返回当前步骤时，控制脚本同时计算：

    allowed_targets =
        已实际访问的步骤
      + 当前步骤
      + 当前步骤的直接后继
      + 路由策略明确授权的前跳目标

使用访问历史而不是 JSON 中的排列位置。分支中没有执行过的步骤，不会仅因为排列在当前步骤之前就自动成为恢复目标。

特殊目标 __complete__ 只有在当前步骤被 workflow 授权完成时才加入集合。

### 前跳策略

| 策略 | 含义 |
|---|---|
| next_only | 默认。只允许当前步骤、已访问步骤和直接后继 |
| declared | 额外允许步骤显式声明的前跳目标 |
| any_defined | 允许选择任意已定义后续步骤，仅用于低风险自治流程 |

推荐原则：

> 回退可以宽松，前进必须受控。

declared 适合简单需求跳过探索等短流程场景；any_defined 不应作为开发、发布和数据迁移流程的默认值。

## 提供给模型的上下文

do 足够指导步骤执行，但通常不足以指导路由。路由时只提供与当前决定相关的最小上下文。

### 当前检查结果

    {
      "current_step": "regression_test",
      "last_check": {
        "passed": false,
        "evidence": "TC-12 expected status=PAID, actual=PENDING"
      }
    }

### 已访问步骤摘要

    {
      "visited_steps": [
        {
          "step": "requirements",
          "result": "passed",
          "summary": "支付成功后订单状态必须为 PAID"
        },
        {
          "step": "implementation",
          "result": "passed",
          "summary": "修改 OrderService#pay"
        }
      ]
    }

不提供完整对话历史。摘要应保留步骤完成结论和路由所需证据。

### 合法候选步骤卡片

    {
      "allowed_targets": [
        {
          "id": "implementation",
          "purpose": "实现或修复生产功能",
          "route_when": "需求和测试设计仍正确，但生产实现不满足要求",
          "do": "修改已有类和方法",
          "check": "确认功能行为满足需求"
        },
        {
          "id": "test_generation",
          "purpose": "根据测试设计生成测试",
          "route_when": "测试代码、断言、mock 或 fixture 与设计不一致",
          "do": "生成或修正相关测试",
          "check": "确认设计用例映射到真实测试方法"
        }
      ]
    }

只返回本轮可选步骤，不加载不可选步骤的内容。

### 相关产物状态

只提供路径、哈希、有效性和必要摘要。模型需要深入判断时再读取正文，不预加载所有产物。

### 待处理人工反馈

人工反馈是路由和执行上下文的一部分。控制面保存尚未处理的反馈，并在模型可以继续执行前将其注入当前上下文：

    {
      "pending_human_feedback": [
        {
          "id": "HF-31",
          "message": "这里先不要继续改，重新确认支付成功的定义",
          "control": "message",
          "delivery": "delivered"
        }
      ]
    }

自然语言反馈由模型理解，不要求人第一次表达时就选择固定的反馈类型。模型需要说明自己如何理解反馈，以及决定继续、询问还是暂停：

    {
      "feedback_id": "HF-31",
      "acknowledged": true,
      "understanding": "需要停止当前实现并重新确认支付状态语义",
      "decision": "continue | ask | pause",
      "reason": "该决定涉及业务语义，现有证据无法唯一确定",
      "next_action": "等待用户确认"
    }

三种决定的含义：

| 决定 | 含义 |
|---|---|
| continue | 反馈含义明确，模型说明调整和影响后继续执行 |
| ask | 涉及人的意图、重大取舍或关键歧义，暂停受影响工作并请求确认 |
| pause | 人明确要求停止，或继续执行存在不可接受风险，停止启动新动作 |

人可以在模型误解委婉反馈时继续补充更明确的要求。系统必须保证新反馈不会因为长任务、上下文压缩或子任务执行而丢失。

反馈状态至少区分：

- delivered：反馈已写入当前任务事件流。
- observed：模型已读取反馈。
- acknowledged：模型已说明对反馈的理解和处理决定。
- applied：反馈已经影响后续计划或执行。

消息发送成功不等于模型已经感知和采纳。控制面应向人暴露这些状态，以便人在模型没有停下时进一步澄清或发出明确控制命令。

### 反馈终态与后续关注

Agent 不依赖对话记忆判断某条反馈是否还需要处理，而是完全依据控制面保存的状态：

- delivered、observed 和 acknowledged 都是未终结状态。`next`、宿主 Hook 和业务动作门禁继续关注这些反馈。
- applied 是反馈生命周期的终态。控制面不再通过 `next` 返回该反馈，不再因它阻断新业务动作，宿主 Hook 也不再重复提醒。
- applied 的反馈仍保留在 inbox 和 events.jsonl 中用于审计、恢复和解释后续决定，不因终结而删除。

`applied` 表示反馈已经实际影响后续理解、计划或执行，不表示反馈涉及的所有代码修改已经通过验证。代码和产物是否完成仍由步骤 check、路由门禁和 `step_results` 判断。若后续证据证明处理不充分，应追加新的反馈事件或使相关步骤失效，而不是把原反馈重新改回 delivered。

当 decision=ask 时，原反馈保持 acknowledged，并由 active_question 阻断业务动作。人的回答作为新反馈写入；模型处理回答并关闭 active_question 后，回答反馈和被回答的原反馈都进入 applied，后续不再重复注入。

## 可打断自治与人工介入

Works 采用类似结对编程的可打断自治模式：模型默认持续推进，人可以随时提供方向、质疑和新信息；是否需要人确认通常由模型根据语义和风险判断。

### 反馈感知点

模型不能长时间运行在看不到新消息的封闭循环中。至少在以下边界检查新的人工反馈：

- 开始下一次工具调用之前。
- 每次工具调用返回之后。
- 子 Agent 返回结果之后。
- 当前步骤的 check 完成之后。
- 提交下一步路由之前。
- 宣布完成之前。
- 长时间操作的周期性检查点。

普通反馈在最近的安全边界生效。控制面保存反馈事件，模型读取后自行判断 continue、ask 或 pause。

### 自然语言反馈与硬控制命令

自然语言反馈属于协作语义，例如“这里感觉不对”或“是不是应该先停一下”，由模型结合上下文判断。人不需要预先掌握结构化指令，也可以在模型理解错误时逐步加强表达。

明确的暂停、取消或停止命令属于控制语义，不由模型决定是否执行：

    {
      "type": "control",
      "action": "pause",
      "reason": "立即停止当前实现，不要启动新的工具调用"
    }

收到硬暂停后，控制面必须停止启动新动作，尽可能取消可取消的长操作，并在最近的安全边界保存一致状态。模型恢复后首先解释自己对暂停原因和当前状态的理解。

因此权限边界是：

- 模型判断普通反馈是否需要确认。
- 人可以通过更明确的反馈纠正模型的理解。
- 控制面保证硬暂停确定生效。
- 高风险、不可逆或超出权限的动作仍由控制面强制审批。

### 渐进明晰的需求

开发过程中产生的新认识不要求重启整个 workflow。新的需求、约束或纠正作为追加事件保存，模型基于当前状态评估：

- 哪些已有工作仍然可用。
- 哪些结论或产物需要修改。
- 哪些检查必须重新执行。
- 是否存在需要人决定的业务取舍。

只有最终目标已经根本改变、原 workflow 不再适用，或当前状态无法可靠修复时，才应结束当前运行并创建新目标。一般情况下采用“吸收反馈、评估影响、当前状态修复、重新验证”的连续过程。

## 路由提交协议

模型必须提交目标和完整判断依据：

    {
      "target": "implementation",
      "reason": "TC-12 与需求一致，测试断言也一致，但生产代码返回 PENDING",
      "still_valid": [
        "requirements",
        "test_case_design",
        "test_generation"
      ],
      "invalidated": [
        "implementation",
        "compile",
        "regression_test"
      ],
      "evidence": "OrderService.java:83 未更新支付成功后的订单状态"
    }

控制脚本必须校验：

1. target 是当前 allowed_targets 中的值。
2. target、still_valid 和 invalidated 中的步骤均已定义。
3. reason 和 evidence 非空。
4. still_valid 与 invalidated 不重叠。
5. 选择完成时 __complete__ 已获当前步骤授权。

脚本不判断业务理由是否正确。理由用于审计、恢复上下文和后续模型判断。

## 非法路由

模型构造不存在的步骤或选择未授权目标时，脚本拒绝推进并返回本轮合法选项：

    {
      "ok": false,
      "error": "E_INVALID_TARGET",
      "target": "invented_step",
      "allowed_targets": [
        "implementation",
        "test_generation",
        "regression_test"
      ]
    }

模型必须基于该列表重新选择，不能通过修改步骤名称绕过 workflow。

## 重试、修复和推进

- 选择当前步骤：重试。
- 选择已访问步骤：将该业务环节重新打开，在当前状态上修复。
- 选择直接后继：正常推进或进入分支。
- 选择显式授权的更远步骤：短流程前跳。
- 选择 __complete__：完成，仅在获得授权时有效。

控制面可以记录路由次数：

    {
      "route_counts": {
        "regression_test->regression_test": 2,
        "regression_test->implementation": 1
      }
    }

次数用于防止无限循环和提供诊断，不用于理解业务失败原因。

## 约束的意义

路由约束不替代模型判断，而是限制模型决定的执行权限。

模型仍负责开放式推理；控制面防止：

- 虚构步骤。
- 因完成偏置跳过检查。
- 未授权前跳。
- 从中间步骤直接宣布完成。
- 上下文压缩后误记 workflow。
- 同一状态下执行超出 workflow 作者授权的动作。

如果某个低风险 workflow 希望完全自治，可以使用 any_defined 放宽限制。约束应保护真实不变量，不能只制造形式上的安全感。

## 落地实现方案

### 当前实现差距

当前 Works 控制面仍是固定状态转移实现：

- state.json 主要保存 current_step、last_check、failures 和少量业务产物元数据。
- check 通过或失败后，控制面直接按 on_success 或 on_failure.goto 选择目标。
- CLI 只有 init、status 和 check，没有人工反馈、暂停、目标修订和模型路由提交入口。

目标架构应在保留现有 validator 和原子状态写入能力的基础上渐进扩展，不要求一次重写全部控制面。

### 持续任务目录

一次开发对应一个可持续恢复的 work，而不是绑定到一个模型上下文窗口或一次不间断会话。推荐目录：

    .works/
      state.json
      events.jsonl
      goal.json
      decisions.json
      inbox/
        HF-001.json
        HF-002.json
      artifacts/

文件职责：

| 文件 | 职责 |
|---|---|
| state.json | 当前状态投影，用于快速恢复 |
| events.jsonl | 追加式事件历史，用于审计和必要时重建状态 |
| goal.json | 当前有效目标、验收条件、约束和 revision |
| decisions.json | 当前有效决定、被替代决定和开放问题 |
| inbox/ | 人工反馈和控制命令的并发安全收件箱 |
| artifacts/ | 需要由 Works 管理的证据和产物元数据 |

每条人工反馈使用独立文件写入 inbox，并通过临时文件加原子替换提交，避免人与 Agent 同时改写 state.json。state.json 仍由控制面单点更新。

### 状态模型

execution_state 与 current_step 必须独立：

    {
      "version": 6,
      "execution_state": "running",
      "current_step": "implementation",
      "visited_steps": [
        "requirements",
        "exploration",
        "implementation"
      ],
      "goal_revision": 3,
      "pending_feedback": ["HF-031"],
      "active_question": null,
      "route_history": [],
      "step_results": {
        "requirements": {
          "status": "verified",
          "summary": "支付结果以验签回调为准"
        },
        "implementation": {
          "status": "active"
        }
      }
    }

execution_state 至少支持：

| 状态 | 含义 |
|---|---|
| running | 可以领取并执行下一原子动作 |
| interrupt_requested | 已收到中断，等待进入安全边界 |
| waiting_for_human | 模型提出了必须由人决定的问题 |
| paused | 硬暂停已经生效，不得启动新动作 |
| completed | 所有完成条件和门禁均已满足 |

例如人工暂停 implementation 时，current_step 仍是 implementation，只有 execution_state 变为 paused。恢复后模型继续基于当前工作区判断，不伪造步骤或时间回滚。

### 人工反馈接口

CLI 第一阶段增加：

    works feedback "这里先别继续，重新确认支付成功的定义"
    works feedback-list
    works feedback-respond HF-031 --decision ask \
      --understanding "需要重新确认支付成功的业务定义" \
      --reason "现有证据无法唯一确定"
    works pause --reason "停止当前实现"
    works resume

普通反馈写入：

    {
      "id": "HF-031",
      "kind": "message",
      "message": "这里先别继续，重新确认支付成功的定义",
      "status": "delivered",
      "created_at": 1787310000
    }

硬控制命令写入：

    {
      "id": "HF-032",
      "kind": "control",
      "action": "pause",
      "reason": "不要再启动新的修改",
      "status": "delivered"
    }

控制面必须优先应用硬控制命令。普通反馈由模型解释，硬暂停不等待模型同意。

### 统一 next 接口

Agent 不直接根据 state.json 猜测下一动作，而是通过统一入口领取一个原子动作：

    works next

优先级从高到低为：

1. 应用尚未生效的硬控制命令。
2. 返回尚未被模型响应的人工反馈。
3. 返回 active_question 并保持等待。
4. 返回当前步骤的执行或检查合同。
5. 返回需要模型提交的路由决定。
6. 在完成获得授权时返回 __complete__。

存在普通反馈时，示例响应：

    {
      "ok": true,
      "execution_state": "running",
      "next_action": {
        "type": "interpret_feedback",
        "feedback": {
          "id": "HF-031",
          "message": "这里先别继续，重新确认支付成功的定义"
        },
        "allowed_decisions": ["continue", "ask", "pause"]
      }
    }

存在硬暂停时，next 不返回业务步骤：

    {
      "ok": true,
      "execution_state": "paused",
      "next_action": null
    }

只要存在未响应的阻断反馈、active_question 或硬暂停，控制面就拒绝新的业务路由和完成请求。

### 反馈响应

模型对普通反馈提交：

    {
      "feedback_id": "HF-031",
      "decision": "ask",
      "understanding": "需要重新确认支付成功的业务定义",
      "reason": "同步响应和异步回调存在两种合理语义",
      "impact": {
        "keep": ["支付网关封装"],
        "modify": ["状态转换逻辑"],
        "reverify": ["回调验签", "幂等性"]
      },
      "question": {
        "text": "回调前订单应保持 PENDING 吗？",
        "options": ["保持 PENDING", "新增 PROCESSING"]
      }
    }

控制面根据 decision 转移执行状态：

- continue：反馈变为 applied，允许领取下一动作。
- ask：反馈保持 acknowledged，保存 active_question，进入 waiting_for_human。
- pause：反馈变为 applied，进入 paused，停止启动新动作。

人的后续回答作为新的反馈事件写入，不覆盖原事件。模型对回答完成解释后关闭 active_question，将回答和原问题反馈标记为 applied，并继续当前 work。

### 可修订 Goal

goal.json 保存当前有效目标，而不是只保存启动时的一句提示：

    {
      "revision": 4,
      "objective": "完成异步支付流程",
      "acceptance_criteria": [
        "验签回调成功后订单变为 PAID",
        "重复回调不会重复处理",
        "同步接口不直接确认支付成功"
      ],
      "constraints": [
        "保持现有查询 API 兼容"
      ],
      "open_questions": []
    }

增加目标修订入口：

    works goal-revise --reason "确认支付结果为异步" \
      --requirement requirement.md

目标修订产生追加事件，记录旧 revision、新 revision、原因和需求文件哈希。控制面不自行判断业务影响，只把依赖旧目标的历史结果标记为 needs_revalidation，并要求模型提交影响分析和后续路由。

一般需求澄清继续留在当前 work。只有最终用户价值根本变化、原 workflow 已不适用或当前状态无法可靠修复时，才结束当前 work 并创建新目标。

### 模型路由接口

workflow 从固定 on_success/on_failure 逐步迁移到 next 和 forward_policy。模型通过 route 提交目标：

    works route --target implementation \
      --reason "需求已确认，但当前状态转换实现不符合新需求" \
      --evidence "OrderService.java:83" \
      --still-valid requirements exploration \
      --invalidated implementation compile regression_test

控制面验证 allowed_targets、步骤存在性、完成授权、阻断反馈以及理由和证据完整性。验证通过后追加 route 事件、更新 visited_steps 和 current_step；控制面不判断业务理由是否正确。

现有 validator 继续承担确定性的产物和证据检查。动态路由替换的是固定跳转选择，不替换 validator。

### 恢复包

每次新会话、上下文压缩或 Agent 重新唤醒时，只需执行 status 和 next。响应至少包含：

    {
      "goal": {
        "revision": 4,
        "objective": "完成异步支付流程",
        "acceptance_criteria": []
      },
      "execution_state": "running",
      "current_step": "implementation",
      "current_step_contract": {},
      "pending_feedback": [],
      "active_question": null,
      "recent_decisions": [],
      "last_check": {},
      "allowed_targets": []
    }

恢复包只加载当前决定所需的最小上下文。需要追溯时再读取 events.jsonl、decisions.json 或相关产物，不依赖完整聊天历史。

### 宿主执行循环

仅实现 CLI 不能保证长任务中的反馈可达。Codex、Claude Code 或其他宿主必须将执行拆成原子动作，并在每个边界重新调用 next：

    while not finished:
        action = works.next()

        if action.execution_state == "paused":
            wait_for_resume()
            continue

        if action.type == "interpret_feedback":
            response = agent.interpret(action.feedback)
            works.respond(response)
            continue

        result = agent.execute_one_atomic_action(action)
        works.record_result(result)

Agent 一次只能领取一个原子动作。工具返回、子 Agent 返回、check 完成和路由提交前必须重新检查 next，不能一次领取完整 workflow 后在控制面之外运行到底。

长时间命令应使用可轮询、可取消的子进程。普通反馈可以在最近的安全边界交给模型解释；硬暂停由宿主或控制面独立监听，停止启动新动作并尽可能取消仍在运行的可取消命令。

### 分阶段实施

#### M1：人工反馈闭环

- 实现 feedback、feedback-list、feedback-respond、pause、resume 和 next。
- 未响应的阻断反馈禁止完成。
- 覆盖 delivered、observed、acknowledged、applied 状态测试。
- 覆盖硬暂停优先于业务动作的测试。

#### M2：可修订 Goal

- 实现 goal.json、goal-revise、revision 和内容哈希。
- 目标变化后标记 needs_revalidation。
- status/next 返回最小恢复包。

#### M3：动态路由

- 实现 visited_steps、allowed_targets 和 route。
- 实现 still_valid、invalidated、route_history 和 __complete__ 授权。
- 拒绝不存在、未授权和存在阻断反馈时的目标。

#### M4：宿主实时集成

- 在所有工具、子 Agent、check、route 和 complete 边界调用 next。
- 支持长命令轮询与取消。
- 将会话中的新用户消息可靠写入 inbox。
- 向人展示 delivered、observed、acknowledged、applied 和当前 execution_state。

第一版不引入复杂的 claim 依赖图。先验证“反馈可靠送达、模型明确响应、目标可修订、状态可恢复和动态路由受控”的闭环；只有真实使用证明步骤级失效粒度不足时，再增加结论和依赖关系模型。

## 非目标

本架构明确不引入：

- 失败原因枚举体系。
- 任意条件表达式语言。
- 固定业务对象的 inputs/outputs DSL。
- 由控制脚本判断需求复杂度或失败根因。
- 为每一步强制创建独立文件。
- 向模型加载完整 workflow、完整对话或全部项目内容。

## 目标状态示例

    {
      "current_step": "regression_test",
      "visited_steps": [
        "requirements",
        "exploration",
        "implementation",
        "compile",
        "regression_test"
      ],
      "last_check": {
        "passed": false,
        "evidence": "相关测试返回状态不符合需求"
      },
      "next_action": {
        "step": "regression_test",
        "allowed_targets": [
          {
            "id": "implementation",
            "purpose": "实现或修复生产功能",
            "route_when": "生产实现不满足当前有效需求"
          },
          {
            "id": "regression_test",
            "purpose": "执行相关测试",
            "route_when": "已有结果仍有效，只需重新执行"
          }
        ]
      }
    }

该状态只暴露有限、合法且语义充分的选择空间。模型决定选择哪个目标，脚本保证选择不会越过 workflow 的安全边界。
