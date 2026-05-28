# Intent Analysis: Research (调查研究)

## 核心挑战

Research 意图有两个独特的失败模式:
1. **无边界研究 (Research without Exit Criteria)**: AI 持续搜索但永远不会说"够了"，产生信息过载而非决策支持
2. **低质量研究 (Shallow Research)**: 满足于前两个搜索结果而非深入挖掘，产生表面信息而非真正的洞察

## Phase 1: 探索先于提问 (Explore Before Asking) — 强制协议

研究请求几乎总能从外部搜索中获益。**在向用户提问之前，先并行启动多条搜索轨道。**

### Step 1.1: 研究问题结构化

将用户的研究请求分解为 2-4 个**子问题**，每个子问题启动一条独立的并行研究轨道:

```
用户问: "research the best approach for real-time notifications in our system"

子问题分解:
Track 1: 技术方案概览 (WebSocket vs SSE vs Long Polling vs Web Push)
Track 2: 与现有技术栈的兼容性 (如果已知技术栈)
Track 3: 可扩展性方案 (单机 → 集群的迁移路径)
Track 4: 实现复杂度对比 (不同方案的代码量、基础设施需求)
```

### Step 1.2: 委托研究

**委托给 `sw-external-researcher`**，为每条轨道提供精确的搜索指令:

```
Track 1 指令: "Research real-time notification delivery mechanisms.
  Compare WebSocket, SSE, Long Polling, and Web Push API across:
  - Browser support, latency, server resource usage, connection limits.
  Find official MDN docs and production usage examples."

Track 2 指令: "Research [已知技术栈/语言] integration with real-time protocols.
  Find official libraries, community best practices, and production case studies."
```

如果需要内部代码库调查:
```
Delegate to sw-codebase-explorer:
"Find any existing real-time communication code in the codebase.
 Search for: WebSocket, SSE, EventSource, socket.io, polling, push notification,
 message queue consumer."
```

### Step 1.3: 整合研究结果

研究完成后，组织为:
- **已证实的事实** (有明确引用来源)
- **社区共识** (多个独立来源一致)
- **观点/偏好** (单一来源或明显有倾向的观点)
- **信息缺口** (仍需进一步研究或需用户决策)

## Phase 2: 研究结构定义

### 研究深度选择

并非所有研究都需要相同的深度。定义四个深度级别:

| 深度级别 | 适用场景 | 行动 | 时间预算 |
|----------|---------|------|---------|
| **Quick Scan** | "before our meeting, find out..." | 2-3 条并行搜索，快速摘要 | ~15 min |
| **Standard Research** | 技术选型、方案对比 | 4-6 条并行搜索 + 交叉验证 | ~30 min |
| **Deep Dive** | 关键架构决策依赖 | Standard + 源码级分析 + 社区输入 | ~1 hr |
| **Comprehensive** | 技术战略、大方向选择 | Deep Dive + 安全分析 + 迁移路径 | ~2 hr |

**默认深度**: Standard Research (除非用户有明确说明)。

**提升深度的触发条件**:
- 研究结果用于架构决策 → 提升到 Deep Dive
- 研究结果涉及安全/合规 → 提升到 Deep Dive
- 研究结果影响团队 6+ 个月的开发 → 提升到 Comprehensive

### 信息来源优先级

```
高优先级 (优先使用):
1. 官方文档 (docs.<project>.io, <project>.org/docs)
2. 源码 (GitHub, GitLab)
3. RFC / 规格文档 (IETF, W3C)
4. 项目 Issue/PR 讨论 (解决过的类似问题)

中优先级 (参考使用):
5. 技术博客 (项目维护者 / 知名从业者的博客)
6. 技术会议演讲 (和当前版本相关的)
7. 技术书籍 (经典参考书)

低优先级 (谨慎使用):
8. 一般技术博客 / Medium 文章
9. 论坛讨论 (StackOverflow, Reddit)
10. LLM 生成的内容 (不可作为第一手来源)
```

## Phase 3: 退出标准 (Exit Criteria)

### 定义退出条件

研究开始时就必须定义退出标准。没有退出标准的研究会无限进行。

**标准退出条件** (选择适用的):

```
□ 回答了所有预定义的子问题
□ 找到了至少 2 个独立的、可信的来源支撑每个关键结论
□ 识别了主要的方案选项 (至少 2 个)
□ 对每个方案记录了 pros/cons
□ 发现了与现有系统的集成考量
□ 未覆盖的边缘情况已被明确标记为 "out of scope"
```

**增强退出条件** (Deep Dive / Comprehensive):

```
□ 对关键结论的源码级验证 (看了实际代码，不是引用博客)
□ 社区趋势分析 (GitHub stars trend, npm downloads trend, 社区活性)
□ 与现有决策记录 (ADR) 的一致性检查
□ 安全/合规影响评估
```

### 何时停止

如果遇到以下情况，不应继续搜索:
- 连续 2 条搜索未产生新信息 (信息收敛)
- 搜索结果大量重复 (饱和)
- 研究预算耗尽 (时间盒到期)

此时应:
1. 标注信息收敛程度: "信息已收敛" / "信息仍不完整"
2. 标注剩余不确定性
3. 建议是否需要更深度的研究

## 应问的问题

仅在探索完成后，针对信息缺口提问 (最多 3 个):

1. **深度确认** (必问):
   ```
   "研究需要到什么深度?
   - Quick Scan: 快速了解有哪些方案 (15 min 级别)
   - Standard: 方案对比与优缺点分析 (30 min 级别)
   - Deep Dive: 源码分析 + 社区深度调研 (1 hr 级别)"
   ```

2. **应用场景** (影响研究方向):
   ```
   "研究结果将如何被使用?
   - 用于架构决策? → 需要 trade-off 分析和长期影响评估
   - 用于实现参考? → 需要具体的代码示例和最佳实践
   - 用于技术演讲/文档? → 需要概念解释和可视化
   - 用于否决/确认某个方案? → 需要明确的适用/不适用场景"
   ```

3. **约束输入** (减少无用研究):
   ```
   "是否有已知约束可以缩小研究范围?
   - 必须/不能使用的特定技术?
   - 许可证限制 (只能用 MIT/Apache 等)?
   - 合规要求 (SOC2, GDPR, etc.)?"
   ```

## Planner Directives for Research Intent

### MUST 指令

```
MUST define exit criteria BEFORE starting research — stating when enough is enough.
MUST launch at least 2 parallel investigation tracks for research questions.
MUST cite primary sources (official docs, source code) over secondary sources (blogs, tutorials).
MUST mark gaps where findings are uncertain or speculative.
MUST organize findings by confidence level: confirmed / community consensus / opinion / speculative.
```

### SHOULD 指令

```
SHOULD decompose broad research questions into 2-4 focused sub-questions.
SHOULD verify key findings with at least 2 independent sources.
SHOULD include "do nothing" / "current state" as a baseline option in comparisons.
SHOULD set a time budget for research and report if exceeded.
```

### MAY 指令

```
MAY elevate research depth from Standard to Deep Dive if findings will influence architecture decisions.
MAY defer implementation-specific details to execution phase.
```

## QA / Acceptance Criteria for Research

1. **[Check]** 退出标准满足:
   ```
   验证: 在启动时定义的退出标准，全部勾选完成
   检查: 输出中包含退出标准检查清单
   ```

2. **[Check]** 来源引用:
   ```
   验证: 每个关键结论至少有 1 个明确的引用来源
   检查: 引用格式包含 URL 或明确的文档章节引用
   ```

3. **[Check]** 信息置信度标记:
   ```
   验证: 所有发现都标记了置信度级别
   Confirmed (2+ 独立官方来源)
   Consensus (社区广泛认同但非官方声明)
   Opinion (单一来源或争议中)
   Speculative (推断而非证据支持)
   ```

4. **[Check]** 选项覆盖:
   ```
   验证: 研究结果至少覆盖了 2 个方案选项
   验证: 包含了 "maintain current state" 作为基线选项
   ```

5. **[Check]** 信息缺口标记:
   ```
   验证: 研究中未覆盖的领域被显式标记
   格式: "Not Covered: [领域], Reason: [超出范围/信息不可得/需要进一步研究]"
   ```
