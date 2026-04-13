# 需求理解与澄清

## What Success Looks Like

Requirements are captured in a structured format that unambiguously defines:
- What problem is being solved
- Who the stakeholders are
- What constraints exist (time, budget, technology, regulatory)
- What "done" looks like — measurable acceptance criteria
- Edge cases and boundary conditions

## Your Approach

**Listen first.** Let the human describe the problem space freely. Ask clarifying questions to expose assumptions, not to challenge.

**Use these lenses:**
- **Scope** — What's in, what's explicitly out
- **Actors** — Who benefits, who uses, who decides
- **Constraints** — Non-negotiable boundaries
- **Success metrics** — How do we know it worked

**When to push deeper:**
- Vague success criteria ("good user experience") → ask for specific measures
- Missing acceptance tests → "How would you verify this works?"
- Unstated assumptions → "What do you take for granted that might not be true?"

**Do not:**
- Rush to solutions before problem is clear
- Assume familiarity with the domain
- Accept "we'll figure it out later" on critical details

## Output Format

Produce a `requirements.md` in the project root with:

```markdown
# Requirements: {feature name}

## Problem Statement
{1-2 sentences on the core problem}

## Scope
**In scope:**
- {bullet}

**Out of scope:**
- {bullet}

## Stakeholders
| Role | Interest | Influence |
|------|----------|-----------|
| {name} | {what they care about} | {high/med/low} |

## Acceptance Criteria
| ID | Criteria | Verification Method |
|----|----------|---------------------|
| AC-1 | {specific, measurable} | {how to verify} |

## Constraints
- {constraint 1}
- {constraint 2}

## Risks & Assumptions
| Risk/Assumption | Impact | Mitigation |
|-----------------|--------|------------|
| {text} | {high/med/low} | {mitigation} |
```

## Memory Integration

After requirements are captured, write summary to `{project-root}/_bmad/memory/hw-shared/tasks.yaml` under a preliminary task entry with status `requirements_captured`.
