# ValueAssessment: 需求价值评估

## What Success Looks Like

Each requirement has a clear value score with specific reasoning, not vague assertions.

## Your Approach

### Assess Each Requirement

Read the requirement document or description. Evaluate:

```
Impact维度:
- 用户价值: 解决什么用户问题?
- 业务价值: 带来什么业务收益?
- 战略价值: 符合长期目标吗?

Effort维度:
- 开发成本: 估计工作量
- 维护成本: 长期维护负担
- 机会成本: 做这个会放弃什么?

Risk维度:
- 技术风险: 实现难度如何?
- 市场风险: 用户会买单吗?
- 执行风险: 我们能完成吗?
```

### Value Score Calculation

```
价值分数 = (Impact × 0.4) + (Strategic Fit × 0.3) + (ROI × 0.3)

Impact: 1-5
Strategic Fit: 1-5
ROI: Impact / Effort (1-5)
```

### Output Format

```markdown
## 价值评估: {需求名称}

**需求ID**: REQ-XXX
**评估时间**: YYYY-MM-DD
**评估人**: hw-value-judgment

### 价值评分: X/5 ({等级})

### Impact分析
| 维度 | 评分 | 说明 |
|------|------|------|
| 用户价值 | X | ... |
| 业务价值 | X | ... |
| 战略价值 | X | ... |

### Effort分析
| 维度 | 评估 | 说明 |
|------|------|------|
| 开发成本 | X人天 | ... |
| 维护成本 | X人月/年 | ... |
| 机会成本 | ... | ... |

### Risk分析
| 风险类型 | 等级 | 缓解措施 |
|----------|------|----------|
| 技术风险 | 中 | ... |

### 决策建议

| 选项 | 说明 |
|------|------|
| **优先做** | 高价值, 低风险 |
| **计划做** | 中价值, 需排期 |
| **暂不做** | 低价值或高风险 |
| **重新设计** | 方向有问题 |

### 备注

...
```

## Verification

Before submitting assessment:
- [ ] Impact dimensions scored (1-5)
- [ ] Effort realistically estimated
- [ ] Risks identified
- [ ] Clear recommendation
- [ ] Trade-offs explained

## Output

Write to `{project-root}/_bmad/memory/hw-shared/value-assessment/{requirement_id}.md`
