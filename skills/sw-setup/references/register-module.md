# RegisterModule: 注册模块能力

## What Success Looks Like

All 黑灯工厂 skills are registered in the module help system and accessible.

## Your Approach

### Skills to Register

| Skill | Display Name | Code |
|-------|--------------|------|
| hw-controller | 黑灯工厂总控 | HW-CTLR |
| hw-worktree-controller | Worktree控制 | HW-WT |
| hw-tdd-agent | TDD执行 | HW-TDD |
| hw-reviewer-security | 安全审核 | HW-REV-SEC |
| hw-reviewer-logic | 逻辑审核 | HW-REV-LOG |
| hw-reviewer-performance | 性能审核 | HW-REV-PERF |
| hw-knowledge-agent | 知识库 | HW-KB |
| hw-setup | 模块安装 | HW-SETUP |

### Registration Entry Format

```csv
module,skill,display-name,menu-code,description,action,args,phase,after,before,required,output-location,outputs
黑灯工厂,hw-controller,黑灯工厂总控,HW-CTLR,协调完整研发流程,,anytime,,,false,,
...
```

### Write to module-help.csv

Append entries to `{project-root}/_bmad/module-help.csv`

## Verification

| Check | Expected |
|-------|----------|
| All skills registered | true |
| Menu codes unique | true |
| Help accessible | true |

## Output

Report registered skills count and any errors.
