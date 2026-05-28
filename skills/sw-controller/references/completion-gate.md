# 完成门禁 (Completion Gate)

参考: Sisyphus orchestrator DNA — oh-my-openagent Phase 3 完成检查

## 核心理念

**NO EVIDENCE = NOT COMPLETE.** 没有证据证明完成 = 没有完成。

完成门禁是工作的最后一道防线。在声称 "DONE" 之前，必须用客观证据验证每一项完成条件。不允许出现 "应该没问题"、"看起来 OK"、"Agent 说做完了" 这类主观判断。

## 证据要求

### 文件编辑 → 诊断通过

| 证据类型 | 如何获取 | 通过标准 |
|---------|---------|---------|
| Linter 诊断 | 运行 linter 检查所有修改的文件 | 0 errors, 0 warnings (或 warnings 不高于改动前) |
| 编译/类型检查 | 运行 build/type-check | 编译成功，0 type errors |
| 格式化 | 运行 formatter check | 所有修改文件格式正确 |

### 构建 → exit 0

```
构建成功的证据:
- 构建命令 exit code = 0
- 构建输出中无 error 级别的日志
- 如果构建失败，绝不会说 "本地能跑，CI 的问题"
```

### 测试 → 全部 PASS

| 测试层级 | 证据 | 通过标准 |
|---------|------|---------|
| UT | 测试运行器输出 | 100% PASS (该模块)，无 skip |
| API 测试 | Newman/Jest/Postman 输出 | 100% PASS，exit 0 |
| 覆盖率 | 覆盖率报告 | ≥ domain 阈值 (来自 config) |

### 委托 → 独立验证

委托给子 Agent 的工作，不能只依赖子 Agent 的自报告。必须独立验证：

```
验证委托的步骤:
  1. 子 Agent 报告 "DONE" → 这是声明，不是证据
  2. 阅读子 Agent 的输出产物 → 这是证据
  3. 运行子 Agent 声称已完成的测试 → 这是验证
  4. 检查代码是否符合项目现有模式 → 这是验证
  5. 确认 MUST DO / MUST NOT DO 规则被遵守 → 这是验证
```

### 委托验证矩阵

| 委托类型 | 验证方式 | 验证通过标准 |
|---------|---------|------------|
| sw-tdd-agent | 运行 UT + API 测试 | 100% PASS |
| sw-reviewer-* | 阅读审查报告 | 0 P0, 0 P1, 0 P2 |
| sw-codebase-explorer | 交叉验证搜索结果 | 信息准确，无遗漏关键文件 |
| sw-strategic-advisor | 评估建议合理性 | 建议可行，不违反已知约束 |
| sw-plan-executor | 检查执行结果 | 所有子任务的测试 PASS |

## 完成检查清单

### 代码改动

- [ ] 所有修改的文件通过 linter 诊断 (0 errors)
- [ ] 项目构建成功 (exit 0)
- [ ] 所有 UT 通过 (包括新增和已有)
- [ ] 所有 API 测试通过 (如适用)
- [ ] 测试覆盖率 ≥ 阈值
- [ ] 无 `{占位符}` 或 `TODO` 残留（除非有意为之并有注释说明）

### 委托验证

- [ ] 每个委托的子 Agent 的输出已独立验证
- [ ] 子 Agent 的 MUST DO 规则全部被遵守
- [ ] 子 Agent 的 MUST NOT DO 规则全部未被违反
- [ ] 没有子 Agent 的自报告未经验证就被接受

### 项目一致性

- [ ] 新增代码遵循项目现有模式（从同类文件中确认）
- [ ] 新增代码的命名与现有代码一致
- [ ] 错误处理方式与模块内其他代码一致
- [ ] import/依赖组织方式与项目规范一致

### 文档与状态

- [ ] 相关状态文件已更新 (tasks.yaml, worktree-registry.yaml)
- [ ] 知识库已更新 (如果 knowledge_base_auto_update = true)
- [ ] ADR 已记录 (如果做出了架构决策)
- [ ] 审查报告已归档到 reviews/

### Git 状态

- [ ] 所有变更已提交
- [ ] 提交信息符合规范 (conventional commits)
- [ ] 无未跟踪的构建产物/临时文件
- [ ] 分支与 base_branch 无冲突

## 完成声明格式

当声明完成时，必须附上证据摘要：

```markdown
## 完成声明 — {task_id}

### 代码改动
- 修改文件: {file-list}
- 新增文件: {file-list}
- 改动行数: +{added} / -{removed}

### 测试结果
- UT: {passed}/{total} PASS, 覆盖率 {percent}%
- API: {passed}/{total} PASS, exit 0
- 审查: security PASS, logic PASS, performance PASS (0 P0, 0 P1, 0 P2)

### 委托验证
- sw-tdd-agent: ✅ UT + API 测试独立验证通过
- sw-reviewer-logic: ✅ 审查报告已读取，P0/P1/P2=0
- sw-reviewer-security: ✅ 审查报告已读取，P0/P1/P2=0

### 门禁状态
- GATE 1 (TDD): ✅ PASS
- GATE 2 (审查): ✅ PASS
- GATE 3 (回归): ✅ PASS

### 完成确认
任务 {task_id} 三层门禁全部通过。所有委托已验证。代码遵循项目现有模式。
```

## 不完整状态的处理

### 如果某项检查未通过

```
不标记 DONE → 回到对应阶段修复 → 重新验证 → 重新走完成门禁
```

不允许 "部分完成" — 要么全部通过，要么是 in_progress。

### 如果某项检查无法执行

```
示例: 没有配置 API 测试环境
处理: 标记为 blocked，告知用户缺少什么
      不是: 跳过 API 验证直接标记 DONE
```

### 如果子 Agent 报告存疑

```
怀疑子 Agent 的自报告:
  → 独立运行关键验证（不依赖子 Agent 的输出）
  → 如果验证失败 → 子 Agent 的 DONE 无效 → 重新委托或自行处理
  → 如果验证通过 → 接受
```

## 反模式

### 反模式 1: 信任子 Agent 的自报告

```
❌ Agent 说 "DONE" → 直接接受 → 标记任务完成
✅ Agent 说 "DONE" → 独立验证 → 确认通过 → 标记任务完成
```

### 反模式 2: "看起来没问题"

```
❌ "UT 看起来都绿了" — 没有实际运行
✅ 运行 UT → 确认 output 显示 ALL PASS → 记录结果
```

### 反模式 3: "之前能跑"

```
❌ "这些测试之前能跑，所以应该没问题"
✅ 每次改动后都重新运行全量测试（或至少相关模块的测试）
```

### 反模式 4: 选择性展示证据

```
❌ 报告 "UT: 45/50 PASS" 但不提哪 5 个失败了及原因
✅ 报告完整的测试结果，包括失败的原因分析和处理计划
```

### 反模式 5: 在没有委托时声称完成

```
❌ 总控自行执行了所有工作，但声称 "子 Agent 处理了"
✅ 如果自行处理，完成声明中如实说明 "自行实现，未委托子 Agent"
```

## 与阶段过渡门禁的关系

完成门禁 (Phase 3) 是针对**单个任务**完成的检查。阶段过渡门禁 (`SKILL.md` Phase Transition Rules) 是针对**阶段之间**的检查。两者互补：

```
个体层面: Completion Gate → 每个任务内的完成标准
系统层面: Phase Transition Rules → 所有任务完成后进入下一阶段的标准
```

一个任务通过 Completion Gate 后，并不意味着整个阶段结束。所有任务都通过 Completion Gate 后，再检查 Phase Transition Rules。
```
