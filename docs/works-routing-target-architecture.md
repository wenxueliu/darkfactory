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

模型负责理解检查结果、判断哪些历史结论仍然有效、找到最早失效的步骤，并在合法目标中选择恢复点或正常分支。模型必须同时提交路由理由、仍然有效的步骤和已经失效的步骤。

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

### 正常分支与异常恢复

正常分支用于选择尚未执行的合法路径，例如：

    requirements
      ├── 简单需求 → implementation
      └── 复杂需求 → exploration

短流程必须有充分证据。无法证明可以安全走短流程时，默认走长流程。

异常恢复用于返回已经执行过的步骤。恢复目标依据最早失效的完成条件选择，而不是依据预定义原因类型选择。

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

## 重试、回退和推进

- 选择当前步骤：重试。
- 选择已访问步骤：回退恢复。
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
