# Intent Analysis: Refactoring (重构)

## 核心挑战

Refactoring 的最常见失败模式是 **行为漂移 (Behavior Drift)**: AI 在重构过程中"顺手"修改了逻辑，导致功能改变。这是因为 AI 模型天然倾向于"修复"它认为不好的代码，而不是仅仅重组它。

## Phase 1: 预重构验证清单 (Pre-Refactor Verification)

在生成任何重构指令之前，必须先确认以下内容:

### V1: 现有测试覆盖确认

```
问题: 哪些测试验证当前行为?
行动: 确定测试套件的范围和状态
```

- 定位与目标模块相关的所有测试文件
- 确认测试当前状态: 全部通过 / 部分通过 / 无测试
- **如果无测试**: 必须向用户提出 — "没有测试保护的重构是有风险的。是否先生成 characterization tests (特征测试)?"
- **如果测试不通过**: 必须先修复，再重构 — "现有测试未通过。重构前必须先让 test suite 变绿。"

### V2: 行为边界定义

```
问题: 什么是"行为不变"的具体定义?
行动: 明确哪些行为必须保持，哪些行为可以改变
```

必须明确的边界:
| 边界维度 | 必须保持不变 | 可以改变 |
|----------|-------------|---------|
| 公开 API 签名 | ✅ | ❌ (除非是重构目标) |
| API 返回值 | ✅ | ❌ |
| 异常/错误行为 | ✅ | ❌ |
| 性能特征 | 需确认 | 需确认 |
| 内部实现 | ❌ | ✅ (重构目标) |
| 私有方法/结构 | ❌ | ✅ (重构目标) |
| 日志格式 | 需确认 | 需确认 |

### V3: 依赖影响分析

```
问题: 哪些外部代码依赖被重构的模块?
行动: 识别所有调用方，评估影响面
```

- 列出所有依赖此模块的调用方
- 如果公开 API 签名不变: 影响仅限内部，低风险
- 如果公开 API 需要变更: 评估影响所有调用方的工作量

## Phase 2: 重构范围检测

### 合法的重构操作

这些操作属于重构，在行为不变的前提下安全:
- Rename (变量/函数/类/文件)
- Extract (函数/类/模块/变量)
- Inline (函数/变量)
- Move (函数/类/文件 between modules)
- Reorganize (文件结构/目录)
- Simplify (条件表达式、循环)
- Replace magic numbers with constants
- Remove dead code (需确认确实是 dead code)

### 容易越界的伪重构

这些操作看似重构，实际上改变行为:
- "Simplify logic" — 如果简化改变了条件判断顺序或有不同的副作用
- "Optimize performance" — 性能优化可能改变算法，属于功能变更
- "Fix potential bug" — 修复 bug 不是重构，是 bugfix
- "Improve error handling" — 改变异常行为不是重构
- "Add type hints" — 通常安全但可能暴露类型不一致需要调整

### 检测信号: 请求中可能隐藏的非重构内容

如果用户请求中出现以下内容，提出澄清问题:
- "also fix..." — 任何 fix 都不是重构
- "improve performance" — 除非明确为"不改变算法的性能改善"
- "make it more robust" — 鲁棒性改善可能改变行为
- "handle edge case" — 处理新边界情况 = 新功能

## 应问的问题 (Questions to Ask)

根据验证结果，选择最关键的 1-3 个问题:

1. **测试覆盖确认** (如果未发现测试):
   ```
   "当前模块似乎缺少测试覆盖。重构前需要 characterization tests 来锁定现有行为。
   是否先由 hw-tdd-agent 为当前行为生成测试? (预估 N 个测试用例)"
   ```

2. **边界确认** (如果边界模糊):
   ```
   "重构的边界是什么? 具体来说:
   - Public API (签名) 是否保持不变?
   - 错误行为是否保持不变?
   - 是否需要保持完全相同的性能特征?"
   ```

3. **重构动机** (帮助生成正确的验证标准):
   ```
   "这次重构的主要目标是什么?
   - 提升可读性? → 验证标准: same tests pass, lint score improved
   - 解耦模块? → 验证标准: same tests pass, import graph simplified
   - 准备扩展? → 验证标准: same tests pass, new extension point exists"
   ```

## Planner Directives for Refactoring Intent

### MUST 指令

```
MUST NOT change any public API signature without explicit authorization.
MUST run the existing test suite BEFORE starting any refactoring and confirm all tests pass.
MUST run the test suite AFTER EVERY refactoring step (not just at the end).
MUST preserve all existing error/exception behavior — no new exceptions, no removed exceptions, no changed exception types.
MUST make minimal changes per commit — each commit should be a single, reversible refactoring operation.
MUST NOT add new functionality during refactoring — new features belong in separate tasks.
```

### SHOULD 指令

```
SHOULD use automated refactoring tools (IDE refactor, static analysis) before manual edits to reduce human error.
SHOULD generate characterization tests if existing test coverage is insufficient.
SHOULD document any behavior-preserving assumptions made during refactoring.
```

### MAY 指令

```
MAY remove dead code after confirming it is truly dead (no references, no reflection access, no config-driven loading).
MAY rename private methods without explicit user confirmation.
```

## QA / Acceptance Criteria for Refactoring

所有验收标准必须 agent-executable:

1. **[Test Command]** 重构前后测试结果一致:
   ```
   重构前: 运行完整测试套件并保存结果: <test-command> > before.txt
   重构后: 运行相同测试套件: <test-command> > after.txt
   验证: 所有 before.txt 中通过的测试在 after.txt 中也通过
   ```

2. **[Static Analysis]** 公开 API 签名未变更:
   ```
   对于每个公开接口，验证:
   - 函数签名 (参数数量、类型、返回值) 未改变
   - 导出的类/常量/类型名称未改变
   工具: 使用 diff 比较重构前后的 public API surface
   ```

3. **[Lint Rule]** 代码质量度量改善:
   ```
   如果重构目标包含可读性/质量改善:
   - Cyclomatic complexity 不增加 (per-function)
   - 函数长度不增加 (per-function)
   - Lint 警告数量不增加
   ```

4. **[Script]** 依赖关系简化 (如适用):
   ```
   如果重构目标包含解耦:
   - 使用 import-graph 工具验证循环依赖减少
   - 模块间耦合度指标改善
   ```

5. **[CI Check]** 无新增 lint warnings:
   ```
   运行 lint 工具，确保重构文件无新增 lint 警告
   ```
