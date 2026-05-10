# ContextMining: 上下文挖掘

## What Success Looks Like

Every accessible information source has been searched. Missed requirements, overlooked decisions, and relevant background context have been identified with specific citations. The implementer knows exactly what they missed and where to find more information.

## Your Approach

Search across 4 source categories. Execute searches in parallel where possible. Document what was searched even when nothing was found.

---

## Source Category 1: Git History (ALWAYS search)

### Recent Changes to Changed Files

```bash
git log --oneline -20 -- <each_changed_file>
```

Look for:
- Recent modifications that explain current code structure
- Reverted commits (indicates previous attempt failed)
- Commit messages referencing issues/PRs not captured in formal specs

### Blame Critical Sections

```bash
git blame <changed_file> | head -50
```

Look for:
- Who wrote the code and when
- Commits that introduced current patterns — check those commit messages for WHY

### Keyword Search in Commit History

```bash
git log --all --oneline --grep="<keywords_from_goal>" -20
```

Extract keywords from the task goal/requirements. Search for related commits across the entire repo. Look for:
- Past work on similar features
- Bug fixes related to this area
- Deprecation notices

### TODO/FIXME/HACK Detection

```bash
git log --all --oneline --grep="TODO\|FIXME\|HACK\|WORKAROUND\|TEMP" -- <changed_paths> -20
```

These markers often indicate known issues or incomplete work that the current implementation should address.

---

## Source Category 2: GitHub (if `gh` CLI available)

### Related Issues

```bash
gh issue list --search "<keywords>" --limit 20 --state all
```

Look for:
- Issues requesting the feature being implemented (may have additional requirements)
- Bug reports in related areas (implementation should not reintroduce fixed bugs)
- Open issues this implementation could close

### Related PRs

```bash
gh pr list --search "<keywords>" --limit 20 --state all
```

For each relevant PR, if accessible:
```bash
gh pr view <pr_number> --comments
```

Look for:
- Review comments that raised concerns about the approach
- Alternative implementations that were rejected (and why)
- Follow-up tasks mentioned in PR descriptions

### GitHub Search for Code References

```bash
gh search code "<keyword>" --repo <owner/repo>
```

Find other files referencing the same patterns, APIs, or modules being changed.

---

## Source Category 3: Communication Channels (if MCP tools available)

### Slack (if Slack MCP available)

Search for:
- Messages mentioning the feature name, changed file names, or related keywords
- Design discussions in team channels
- User bug reports or feature requests
- Warnings from oncall incidents related to this area

Search timeframe: last 90 days minimum.

### Notion/Confluence (if MCP available)

Search for:
- Design docs, RFCs, ADRs related to this feature
- Project briefs with requirements
- Post-mortems mentioning the changed modules
- Onboarding docs describing the system architecture

### Discord (if MCP available)

Search relevant server channels for technical discussions mentioning the feature or changed modules.

---

## Source Category 4: Codebase Cross-References (ALWAYS search)

### Find Importers/Consumers

Search the codebase for files that import, require, or reference the changed modules:

```
# Search for import/reference patterns (adapt to project language)
grep -r "import.*<module_name>" --include="*.py" .
grep -r "require.*<module_name>" --include="*.js" .
grep -r "from <module>" --include="*.py" .
```

These files may break or need updates due to the changes.

### Find Tests Needing Updates

```
# Find test files related to changed modules
glob pattern: **/test*/**/*<module_name>*.*
glob pattern: **/spec/**/*<module_name>*.*
```

Tests that exercise changed behavior must be identified. If behavior changed but tests weren't updated, it's a finding.

### Find Documentation References

```
grep -r "<module_name>\|<feature_name>" README* docs/ *.md --include="*.md" -l
```

Documentation referencing changed behavior must be flagged for updates.

### Find Configuration Files

```
glob pattern: **/*.yaml, **/*.yml, **/*.json, **/*.toml, **/*.conf, **/.env*
```

Check if config files need corresponding updates for new features or changed behavior.

### Find Related Features

Search for files in the same domain/packages as the changed modules. Related features that share patterns or state with the changed code may be affected.

---

## What to Look For

| Category | What to Find | Impact |
|----------|-------------|--------|
| Missed requirements | Requirements in issues/PRs that the implementation doesn't address | BLOCKING |
| Past decisions | Commit messages, PR comments, ADRs explaining WHY code is structured a certain way | IMPORTANT |
| Related systems | Files/modules that import or depend on the changed code | IMPORTANT |
| Developer warnings | TODOs, FIXMEs, HACKs, PR review comments, commit messages with warnings | IMPORTANT |
| Migration notes | Deprecation plans, version upgrade notes affecting changed modules | IMPORTANT |
| Design docs | External design decisions (Notion, Slack, ADRs) that weren't captured in-code | FYI |
| Follow-up tasks | Issues/PRs mentioning post-release follow-ups for the changed area | FYI |

## Finding Format

Each finding must include:

```markdown
### [BLOCKING/IMPORTANT/FYI] Finding Title

- **Source:** Where found (git commit abc123, GitHub issue #42, Slack message link, file:line)
- **Finding:** What was discovered
- **Relevance:** How it relates to the current implementation
- **Recommendation:** What should change (if anything)

### Source Coverage Report

| Source | Status | Details |
|--------|--------|---------|
| git log (changed files) | SEARCHED | 20 commits reviewed, 2 relevant findings |
| git blame | SEARCHED | Critical sections checked |
| git log --grep | SEARCHED | Keywords: "auth", "login" — 5 commits found |
| GitHub issues | SEARCHED | 12 issues reviewed, 1 missed requirement |
| GitHub PRs | SEARCHED | 8 PRs reviewed, 1 relevant review comment |
| Slack | SKIPPED | No Slack MCP configured |
| Notion | SKIPPED | No Notion MCP configured |
| Codebase imports | SEARCHED | 3 importers found, all compatible |
| Related tests | SEARCHED | 2 test files identified, both updated |
| Documentation | SEARCHED | README references need update |
| Config files | SEARCHED | No config changes needed |
```

## Severity Mapping

Context mining uses the standard HW severity system:

| Level | Name | Criteria | Action |
|-------|------|----------|--------|
| P0 | Fatal | Implementation violates a documented constraint or past decision that would cause production failure | Must fix, blocks all phases |
| P1 | Severe | Missing requirement from a formal issue/PR that was explicitly requested | Must fix, blocks next phase |
| P2 | General | Implementation doesn't account for related system behavior or known edge cases documented elsewhere | Must fix, blocks next phase |
| P3 | Suggestion | Documentation should be updated, follow-up task should be created | Document only |

## Verification

Before submitting review:
- [ ] All 4 source categories attempted (git, GitHub, communication, codebase)
- [ ] Every finding has a specific source citation
- [ ] Skipped sources have a reason noted
- [ ] Source coverage report is complete
- [ ] Each finding has severity rating
- [ ] BLOCKING/IMPORTANT findings have actionable recommendations

## Output

Write to `{project-root}/_bmad/memory/hw-shared/reviews/{task_id}-context.md`
