# PriorityRanking: 优先级排序

## What Success Looks Like

Clear优先级 ranking with explicit reasoning when trade-offs are made.

## Your Approach

### Priority Matrix

Use **ICE + Strategic Fit** framework:

```
Priority Score = (I × 0.25) + (C × 0.25) + (E × 0.20) + (S × 0.30)

I = Impact (1-10)
C = Confidence (1-10) 
E = Ease (1-10)
S = Strategic Fit (1-10)
```

### Ranking Process

1. **List all requirements**
2. **Score each dimension**
3. **Calculate priority score**
4. **Group into tiers**
5. **Resolve conflicts**

### Priority Tiers

| Tier | Score | 含义 | 行动 |
|------|-------|------|------|
| P0 | 8-10 | 最高优先 | 立即执行 |
| P1 | 6-7.9 | 高优先 | 本迭代 |
| P2 | 4-5.9 | 中优先 | 下个迭代 |
| P3 | 2-3.9 | 低优先 | 视情况 |
| P4 | <2 | 最低优先 | 暂不做 |

### Conflict Resolution

When priorities conflict:

```markdown
### 冲突: {需求A} vs {需求B}

**冲突点**: 资源有限, 只能选一个

**分析**:
| 维度 | 需求A | 需求B |
|------|-------|-------|
| Impact | X | Y |
| Strategic Fit | X | Y |
| Urgency | X | Y |

**决策**: 选择{需求A/B}
**理由**: {说明}

**风险**: {被放弃需求的后果}
```

### Output Format

```markdown
## 优先级排序报告

**生成时间**: YYYY-MM-DD
**评估范围**: {需求列表}

### P0 - 立即执行
| 需求ID | 名称 | 分数 | 理由 |
|--------|------|------|------|
| REQ-001 | ... | 9.2 | ... |

### P1 - 本迭代
| 需求ID | 名称 | 分数 | 理由 |
|--------|------|------|------|
| REQ-002 | ... | 7.1 | ... |

### P2 - 下个迭代
...

### P3 - 视情况
...

### P4 - 暂不做
...

### 依赖关系
```mermaid
REQ-001 --> REQ-003
REQ-002 --> REQ-004
```

### 资源约束
- 可用人力: X人
- 时间约束: Y周
- 结论: {说明}
```

## Verification

Before submitting ranking:
- [ ] All requirements scored
- [ ] Conflicts identified
- [ ] Dependencies mapped
- [ ] Constraints considered
- [ ] Rationale documented

## Output

Write to `{project-root}/_context/memory/sw-shared/value-assessment/priority-ranking-{date}.md`
