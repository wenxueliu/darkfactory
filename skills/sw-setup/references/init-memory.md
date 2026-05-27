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

For each file below: read the template from `references/<template>` and write it to the target path under `{project-root}/_context/memory/`.

| Target Path | Template Source |
|-------------|----------------|
| `_context/memory/sw-shared/requirements-tracker.yaml` | `references/requirements-tracker-template.yaml` |
| `_context/memory/sw-shared/tasks.yaml` | `references/tasks-template.yaml` |
| `_context/memory/sw-shared/design-decisions.md` | `references/design-decisions-template.md` |
| `_context/memory/sw-shared/human-interventions.md` | `references/human-interventions-template.md` |
| `_context/memory/sw-shared/knowledge-base/index.md` | `references/knowledge-base-index-template.md` |
| `_context/memory/sw-controller/global-state.yaml` | `references/global-state-template.yaml` |
| `_context/memory/sw-controller/worktree-registry.yaml` | `references/worktree-registry-template.yaml` |

### Verify Permissions

Ensure directories are writable by the agent runtime.

## Output

Report created structure and any errors.
