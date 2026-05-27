# InitializeMemory: 初始化共享内存

## What Success Looks Like

The shared memory structure is created with proper permissions and initial content.

## Your Approach

### Create Directory Structure

```bash
# Create all directories
{project-root}/_context/memory/sw-shared/
{project-root}/_context/memory/sw-shared/knowledge-base/
{project-root}/_context/memory/sw-shared/knowledge-base/patterns/
{project-root}/_context/memory/sw-shared/knowledge-base/decisions/
{project-root}/_context/memory/sw-shared/knowledge-base/lessons/
{project-root}/_context/memory/sw-shared/knowledge-base/api-contracts/
{project-root}/_context/memory/sw-shared/reviews/
{project-root}/_context/memory/sw-controller/
```

### Create Initial Files

| File | Content |
|------|---------|
| `requirements-tracker.yaml` | Copy from `references/requirements-tracker-template.yaml` |
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
