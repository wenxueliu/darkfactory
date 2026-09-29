# InitializeMemory: 初始化共享内存

## What Success Looks Like

The shared memory structure is created with proper permissions and initial content.

## Your Approach

### Create Directory Structure

```bash
# Create the project workspace roots. The user places source repositories in services/ after initialization.
{project-root}/services/
{project-root}/knowledge/
{project-root}/knowledge/patterns/
{project-root}/knowledge/decisions/
{project-root}/knowledge/lessons/
{project-root}/knowledge/contracts/
{project-root}/knowledge/domains/
{project-root}/knowledge/services/
{project-root}/knowledge/requirements/
{project-root}/knowledge/reviews/
{project-root}/knowledge/value-assessment/
{project-root}/knowledge/sw-controller/
```

### Create Initial Files

For each file below: read the template from `references/<template>` and write it to the target path shown below.

| Target Path | Template Source |
|-------------|----------------|
| `knowledge/requirements-tracker.yaml` | `references/requirements-tracker-template.yaml` |
| `knowledge/tasks.yaml` | `references/tasks-template.yaml` |
| `knowledge/design-decisions.md` | `references/design-decisions-template.md` |
| `knowledge/human-interventions.md` | `references/human-interventions-template.md` |
| `knowledge/index.md` | `references/knowledge-base-index-template.md` |
| `knowledge/sw-controller/global-state.yaml` | `references/global-state-template.yaml` |
| `knowledge/sw-controller/worktree-registry.yaml` | `references/worktree-registry-template.yaml` |

### Verify Permissions

Ensure directories are writable by the agent runtime.

### Post-initialization source repository requirement

The setup skill does not clone or infer business source code. After initialization, the user must place every repository to be modified under `services/{repository-name}/`. One repository is valid and is handled by the same discovery and gate flow as multiple repositories. An empty `services/` directory is a blocking setup error.

## Output

Report created structure and any errors.
