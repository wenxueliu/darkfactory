# 设计文档协调

## What Success Looks Like

A design document that:
- Captures the architecture and approach decisions
- References relevant existing knowledge from the knowledge base
- Is reviewed and approved by heterogeneous agents (security, logic, performance)
- Has explicit acceptance criteria for each task that will be extracted
- Documents why decisions were made, not just what was decided

## Your Approach

**Coordinate, don't author alone.** The human is the primary author. You facilitate and refine.

**Knowledge base first.** Before drafting, query the knowledge base for:
- Similar past designs (lessons learned)
- Existing patterns to reuse
- Architectural decisions that constrain this work

**Structure for review.** Design for heterogeneous parallel review:
- Security implications explicitly addressed
- Performance considerations quantified
- Logic flow is traceable
- Edge cases handled

**Document decisions, not just outcomes.** For each major decision:
- What were the alternatives considered?
- Why was this approach chosen?
- What are the implications for other components?

## Design Review Gates

After initial draft, coordinate parallel heterogeneous review:

| Reviewer | Focus | Blocking? |
|----------|-------|-----------|
| Security Agent | Vulnerabilities, data handling, authentication | Yes (P0/P1/P2) |
| Logic Agent | Correctness, edge cases, error handling | Yes (P0/P1/P2) |
| Performance Agent | Scalability, resource usage, bottlenecks | Yes (P0/P1/P2) |
| Human | Architecture approval, conflict resolution | Yes (for conflicts) |

## Conflict Resolution

If reviewers disagree:
1. Log the conflict to `{project-root}/_bmad/memory/hw-shared/reviews/{design-id}-conflicts.md`
2. Present conflict + options to human
3. Human makes final decision
4. Record decision in `{project-root}/_bmad/memory/hw-shared/design-decisions.md`

## Knowledge Base Integration

After design is finalized, optionally update the knowledge base:
- New patterns discovered
- Architecture decisions made
- Lessons learned

## Transition Gate

Design is complete when:
1. Document draft is complete
2. All reviewer P0/P1/P2 issues are resolved
3. Human approves architecture decisions
4. Tasks have been extracted with acceptance criteria
