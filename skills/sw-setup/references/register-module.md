# RegisterModule: 注册模块能力

## What Success Looks Like

All 黑灯工厂 skills are registered in the module help system and accessible.

## Your Approach

### Skills to Register

| Skill | Display Name | Code |
|-------|--------------|------|
| sw-controller | 黑灯工厂总控 | HW-CTLR |
| sw-worktree-controller | Worktree控制 | HW-WT |
| sw-tdd-agent | TDD执行 | HW-TDD |
| sw-reviewer-security | 安全审核 | HW-REV-SEC |
| sw-reviewer-logic | 逻辑审核 | HW-REV-LOG |
| sw-reviewer-performance | 性能审核 | HW-REV-PERF |
| sw-knowledge-agent | 知识库 | HW-KB |
| sw-setup | 模块安装 | HW-SETUP |

### Registration Entry Format

```csv
module,skill,display-name,menu-code,description,action,args,phase,after,before,required,output-location,outputs
黑灯工厂,sw-controller,黑灯工厂总控,HW-CTLR,协调完整研发流程,,anytime,,,false,,
...
```

### Write to module-help.csv

Append entries to `{project-root}/_context/module-help.csv`

## Verification

| Check | Expected |
|-------|----------|
| All skills registered | true |
| Menu codes unique | true |
| Help accessible | true |

## Output

Report registered skills count and any errors.
