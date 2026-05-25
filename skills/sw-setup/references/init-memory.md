# InitializeMemory: 初始化共享内存

## What Success Looks Like

The shared memory structure is created with proper permissions and initial content.

## Your Approach

### Create Directory Structure

```bash
# Create all directories
{project-root}/_bmad/memory/hw-shared/
{project-root}/_bmad/memory/hw-shared/knowledge-base/
{project-root}/_bmad/memory/hw-shared/knowledge-base/patterns/
{project-root}/_bmad/memory/hw-shared/knowledge-base/decisions/
{project-root}/_bmad/memory/hw-shared/knowledge-base/lessons/
{project-root}/_bmad/memory/hw-shared/knowledge-base/api-contracts/
{project-root}/_bmad/memory/hw-shared/reviews/
{project-root}/_bmad/memory/hw-controller/
```

### Create Initial Files

| File | Content |
|------|---------|
| `tasks.yaml` | Empty tasks list |
| `design-decisions.md` | Header only |
| `human-interventions.md` | Header only |
| `knowledge-base/index.md` | Index structure |
| `global-state.yaml` | Initial state |
| `worktree-registry.yaml` | Empty registry |

### Verify Permissions

Ensure directories are writable by the agent runtime.

## Output

Report created structure and any errors.
