# 草稿管理 (Draft Management)

草稿是 sw-strategic-planner 的外部工作记忆。在长会话中，上下文窗口是有限的，草稿文件作为 "备份大脑" 确保没有信息丢失。

---

## 草稿文件约定

### 命名约定

```
{project-root}/_context/memory/sw-shared/drafts/{topic-slug}.md
```

- **topic-slug**: 用 kebab-case 描述主题，如 `jwt-auth-plan`, `refactor-user-module`, `dark-mode-feature`
- 如果主题尚未明确，使用描述性短语: `user-auth-discussion`, `api-redesign-exploration`
- 同一会话只有一个活跃草稿——绝不为不同方面创建多个并发草稿

### 文件路径规则

- 草稿仅保存在 `{project-root}/_context/memory/sw-shared/drafts/` 下
- 草稿是 `.md` 文件
- 其他任何路径将被拒绝

---

## 草稿结构模板

当首次创建草稿时，使用此模板:

```markdown
# Draft: {Topic Name}

> 创建于: {date} | 最后更新: {date/time}
> 状态: 访谈中 (Interview Mode)

---

## Request Summary (原始需求摘要)

{用户最初的需求描述，尽可能用用户的原话}

---

## Clarification Log (澄清日志)

### Q1: {question}
- **Asked**: {when}
- **Answer**: {user's answer}
- **Impact**: {how this affects the plan}

### Q2: {question}
- ...

---

## Research Findings (研究发现)

### Finding 1: {topic}
- **Source**: {codebase-explorer / external-researcher / user}
- **Key Point**: {what was discovered}
- **Implication**: {how this affects the plan}

### Finding 2: {topic}
- ...

---

## Key Decisions (关键决策)

- **Decision 1**: {what was decided} — {rationale}
- **Decision 2**: {what was decided} — {rationale}
- ...

---

## Scope Boundaries (范围边界)

### IN SCOPE
- {item 1}
- {item 2}

### OUT OF SCOPE (Explicit Exclusions)
- {item 1}
- {item 2}

---

## Risk Log (风险日志)

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| {description} | high/medium/low | {mitigation strategy} | open/mitigated/accepted |

---

## Test Strategy (测试策略)

- **Infrastructure exists**: YES/NO
- **Automated tests**: TDD / Tests-after / None
- **Framework**: {pytest / jest / vitest / ...}
- **Agent-Executed QA**: ALWAYS

---

## Partial Plan Structure (部分计划结构)

{When enough information is gathered, start sketching the plan structure}

### Anticipated Waves
- Wave 1: {what goes here}
- Wave 2: {what goes here}
- ...

### Key TODOs (tentative)
- [ ] {task description} - {why it's needed}
- ...

---

## Open Questions (待回答问题)

- [ ] {question} — {why it matters} — {priority: high/medium/low}
- [ ] ...

---

## Notes (备注)

{任何不适合其他分类但需要记录的内容}
```

---

## 草稿更新时机 (MANDATORY Triggers)

**在以下情况必须更新草稿：**

| 触发事件 | 更新内容 | 更新方式 |
|---------|---------|---------|
| 首次实质性交换 | 创建草稿 | Write 新文件 |
| 每次用户回答一个问题 | 追加到 Clarification Log | Edit 追加 |
| 探索 Agent 返回结果 | 追加到 Research Findings | Edit 追加 |
| 做出技术决策时 | 追加到 Key Decisions | Edit 追加 |
| 范围被澄清或改变时 | 更新 Scope Boundaries | Edit 替换对应 section |
| 识别到新的风险时 | 追加到 Risk Log | Edit 追加 |
| 新的开放性问题出现时 | 追加到 Open Questions | Edit 追加 |
| 部分计划结构在脑中成型时 | 更新 Partial Plan Structure | Edit 替换对应 section |
| 清关清单某项从不通过变为通过时 | 更新 Notes 记录进展 | Edit 追加 |

**绝不等到 "收集完所有信息" 才写草稿。逐步构建。实时记录。**

---

## 草稿同步规则

### 创建草稿

```markdown
在第一个实质性交流时创建草稿:

Write("{project-root}/_context/memory/sw-shared/drafts/{topic-slug}.md", initialDraftContent)
```

### 追加更新

```markdown
在每个有意义的用户响应或研究结果后:

Edit("{project-root}/_context/memory/sw-shared/drafts/{topic-slug}.md",
  oldString="## Notes",
  newString="## Clarification Log\n\n### Q{N}: {question}\n- **Answer**: {answer}\n- **Impact**: {impact}\n\n## Notes")
```

### 替换更新

当需要更新已有 section 时，使用 Edit 替换旧的 section 内容为新内容。

### 告知用户

```markdown
在草稿创建/首次提及时告知用户:
"我正在将我们的讨论记录在 _context/memory/sw-shared/drafts/{name}.md ——你可以随时查阅。"
```

---

## 为什么草稿至关重要

1. **防止上下文丢失** — 长会话中，早期的共识可能被推出上下文窗口。草稿是永久记录。
2. **外部记忆** — 你的上下文窗口有限。草稿是超过窗口大小的备份记忆。
3. **确保计划完整性** — 计划生成时需要完整的访谈信息。草稿确保没有任何缺失。
4. **用户可以随时审查** — 用户可以阅读草稿验证你的理解，在计划生成前纠正偏差。
5. **中断恢复** — 如果会话中断，草稿保留了所有进展，可以从断点继续。

---

## 草稿更新示例

### 状态更新示例

```
[草稿已更新: _context/memory/sw-shared/drafts/jwt-auth-plan.md]
- 添加: Q3 关于 token 过期策略的回答
- 更新: Scope Boundaries - 明确了 OAuth 不在范围内
- 添加: Key Decision - 使用 JWT access + refresh token 方案

待回答问题: 2 个 (关于 session 存储和 rate limiting)
```

---

## 从草稿到计划

当自动过渡到计划生成时:

1. **完整阅读草稿** — 加载整个草稿文件作为计划生成的上下文
2. **草稿内容映射**:
   - Request Summary -> Plan Context / Original Request
   - Clarification Log -> Plan Context / Interview Summary
   - Research Findings -> Plan Context / Research Findings
   - Key Decisions -> Plan Work Objectives / Must Have + Must NOT Have
   - Scope Boundaries -> Plan Work Objectives / Must NOT Have (Guardrails)
   - Risk Log -> Plan Execution Strategy considerations
   - Partial Plan Structure -> Plan Execution Strategy / Wave structure
   - Open Questions -> Plan [DECISION NEEDED] placeholders
3. **计划完成后删除草稿** (详见 references/handoff-protocol.md)

---

## 草稿反模式

- ❌ **不做草稿** — "我记得住。" 不，你记不住。上下文窗口是有限的。
- ❌ **延迟创建草稿** — "等我有了足够信息再写。" 现在就写，即使是空的框架。
- ❌ **草稿过于简单** — 只说 "用户想要 JWT 认证"，没有记录为什么、范围和约束。
- ❌ **创建多个草稿** — 一个会话只有一个活跃草稿。将不同关注点作为草稿内的 sections。
- ❌ **忘记更新草稿** — 3 轮对话后草稿还是初始版本。你会丢失中间的上下文。
- ❌ **计划生成前不读草稿** — 如果跳过阅读草稿，计划将基于不完整的记忆生成。
