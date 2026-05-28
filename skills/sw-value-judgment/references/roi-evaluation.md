# ROIEvaluation: ROI评估

## What Success Looks Like

Clear ROI calculation with specific numbers, not hand-waving.

## Your Approach

### ROI Framework

```
ROI = (预期收益 - 成本) / 成本 × 100%

收益类型:
- 直接收益: 收入增长, 成本节约
- 间接收益: 效率提升, 用户满意度
- 战略收益: 市场地位, 品牌影响

成本类型:
- 开发成本: 人力, 工具, 基础设施
- 维护成本: 持续投入
- 机会成本: 放弃的其他机会
```

### ROI Calculation

For each requirement, estimate:

| 项目 | 估算值 | 说明 |
|------|--------|------|
| 开发成本 | X人天 | ... |
| 维护成本/年 | X人天 | ... |
| 直接收益/年 | X万元 | ... |
| 间接收益/年 | X万元 | ... |
| 战略收益 | 定性 | ... |

### Break-Even Analysis

```
盈亏平衡点 = 总成本 / (年收益 - 年维护成本)
```

### 输出格式

```markdown
## ROI评估: {需求名称}

**需求ID**: REQ-XXX
**评估时间**: YYYY-MM-DD

### 成本估算
| 成本类型 | 金额/人天 | 备注 |
|----------|-----------|------|
| 开发成本 | X万元 | X人天 |
| 第一年维护成本 | X万元 | ... |
| 三年总成本 | X万元 | ... |

### 收益估算
| 收益类型 | 第一年 | 第三年 | 备注 |
|----------|--------|--------|------|
| 直接收益 | X万元 | X万元 | ... |
| 间接收益 | X万元 | X万元 | ... |

### ROI分析
| 指标 | 值 | 说明 |
|------|-----|------|
| 第一年ROI | X% | ... |
| 三年ROI | X% | ... |
| 盈亏平衡点 | X个月 | ... |

### ROI等级
| 等级 | ROI范围 | 行动 |
|------|---------|------|
| A | >200% | 强烈推荐 |
| B | 100-200% | 推荐 |
| C | 50-100% | 考虑 |
| D | <50% | 不推荐 |
```

## Verification

Before submitting:
- [ ] Costs realistic
- [ ] Benefits specific
- [ ] Timeframe clear
- [ ] Break-even calculated
- [ ] Assumption stated

## Output

Write to `{project-root}/_context/memory/sw-shared/value-assessment/{requirement_id}-roi.md`
