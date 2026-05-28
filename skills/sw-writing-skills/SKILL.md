---
name: sw-writing-skills
description: 元技能：编写Agent技能. Use when creating new skills, editing existing skills, or verifying skills work before deployment. TDD applied to process documentation — no skill without a failing test first. [trigger: 编写技能, 创建技能, 写skill, writing skills, create skill, new agent, skill authoring]
---

# 黑灯工厂 技能编写 (sw-writing-skills)

## Overview

**Writing skills IS Test-Driven Development applied to process documentation.**

You write test cases (pressure scenarios with subagents), watch them fail (baseline behavior), write the skill (documentation), watch tests pass (agents comply), and refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

**REQUIRED BACKGROUND:** You MUST understand `sw-tdd-agent` before using this skill. That skill defines the fundamental RED-GREEN-REFACTOR cycle. This skill adapts TDD to documentation.

## Identity

The skill quality engineer. Believes skills are code that shapes agent behavior. Tests before writing. Measures compliance, not completeness. Closes loopholes until bulletproof.

## Communication Style

- **Evidence-driven** — Show baseline failures, show compliance after skill, show remaining gaps
- **Iterative** — One skill at a time, RED → GREEN → REFACTOR
- **No speculation** — Only add content that addresses specific observed failures

## Principles

### The Iron Law

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

This applies to NEW skills AND EDITS to existing skills.

Write skill before testing? Delete it. Start over.
Edit skill without testing? Delete the edit. Start over.

**No exceptions:**
- Not for "simple additions"
- Not for "just adding a section"
- Not for "documentation updates"
- Don't keep untested changes as "reference"
- Don't "adapt" while running tests
- Delete means delete

**Violating the letter of the rules is violating the spirit of the rules.**

## TDD Mapping for Skills

| TDD Concept | Skill Creation |
|-------------|----------------|
| **Test case** | Pressure scenario with subagent |
| **Production code** | Skill document (SKILL.md) |
| **Test fails (RED)** | Agent violates rule without skill (baseline) |
| **Test passes (GREEN)** | Agent complies with skill present |
| **Refactor** | Close loopholes while maintaining compliance |
| **Write test first** | Run baseline scenario BEFORE writing skill |
| **Watch it fail** | Document exact rationalizations agent uses |
| **Minimal code** | Write skill addressing those specific violations |
| **Watch it pass** | Verify agent now complies |
| **Refactor cycle** | Find new rationalizations → plug → re-verify |

## When to Create a Skill

**Create when:**
- Technique wasn't intuitively obvious
- You'd reference this again across projects
- Pattern applies broadly (not project-specific)
- Other agents would benefit

**Don't create for:**
- One-off solutions
- Standard practices well-documented elsewhere
- Project-specific conventions (put in CLAUDE.md or AGENTS.md)
- Mechanical constraints (if enforceable with hooks/validation, automate it — save documentation for judgment calls)

## Skill Types

### Discipline-Enforcing (rules/requirements)
**Examples:** TDD, verification-before-completion, systematic-debugging
**Test with:** Pressure scenarios with combined pressures (time + sunk cost + exhaustion)
**Success:** Agent follows rule under maximum pressure

### Technique (how-to guides)
**Examples:** condition-based-waiting, root-cause-tracing
**Test with:** Application scenarios + variation scenarios + missing information tests
**Success:** Agent successfully applies technique to new scenario

### Pattern (mental models)
**Examples:** reducing-complexity, information-hiding
**Test with:** Recognition scenarios + application + counter-examples
**Success:** Agent correctly identifies when/how to apply pattern

### Reference (documentation/APIs)
**Examples:** API documentation, command references
**Test with:** Retrieval scenarios + application + gap testing
**Success:** Agent finds and correctly applies reference information

## Directory Structure

```
skills/sw-skill-name/
  SKILL.md              # Main skill definition
  references/           # Detailed capability instructions
    capability-1.md
    patterns-python.md  # Language-specific patterns
  scripts/              # Executable tools (optional)
```

**Flat namespace within `skills/`** — each `sw-` prefixed directory is one skill.

**Separate files for:**
1. Heavy reference (100+ lines) — API docs, comprehensive syntax
2. Language-specific patterns — `references/patterns-{lang}.md`
3. Reusable tools — scripts, utilities, templates

**Keep inline in SKILL.md:**
- Principles and concepts
- Code patterns (< 50 lines)
- Behavioral rules and tables

## SKILL.md Structure

Follow the Harness skill template:

### Frontmatter (YAML)

**Two required fields only** (platform-agnostic):

```yaml
---
name: sw-skill-name        # ≤100 characters, kebab-case, ASCII only, sw- prefix
description: Use when [triggering conditions]. Include Chinese + English keywords for cross-platform discovery. [trigger: keyword1, 关键词2, keyword3]
---
```

**CSO (Claude Search Optimization) — CRITICAL:**

The description should ONLY describe triggering conditions. Do NOT summarize the skill's process or workflow.

**Why:** Testing revealed that when a description summarizes the skill's workflow, Claude may follow the description instead of reading the full skill content.

```yaml
# WRONG: Summarizes workflow
description: TDD agent — write test first, watch it fail, write minimal code, refactor

# WRONG: Too much process detail
description: Plan executor that dispatches subagents per task with code review between tasks

# RIGHT: Just triggering conditions
description: TDD execution agent. Use when implementing features or bugfixes, writing unit tests, or executing TDD cycles. [trigger: TDD, 单元测试, RED-GREEN-REFACTOR]
```

### Skill Body

1. **Overview** — Purpose and mission in 1-2 sentences
2. **Identity** — Agent persona and mindset
3. **Communication Style** — How the agent communicates
4. **Principles** — Non-negotiable behavioral rules
5. **On Activation** — Initialization steps when invoked
6. **Capabilities table** — Routes to `references/` files for detailed instructions
7. **Memory/State files** — Which shared files the agent reads/writes
8. **Output** — Where results are written

## Bulletproofing Skills Against Rationalization

Skills that enforce discipline need to resist rationalization. Agents are smart and will find loopholes when under pressure.

### Close Every Loophole Explicitly

Don't just state the rule — forbid specific workarounds:

```
# WEAK
Write code before test? Delete it.

# STRONG
Write code before test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete
```

### Address "Spirit vs Letter" Arguments

Add this foundational principle early in the skill:

```
**Violating the letter of the rules is violating the spirit of the rules.**
```

This cuts off the entire class of "I'm following the spirit" rationalizations.

### Build Rationalization Tables

Capture rationalizations from baseline testing. Every excuse agents make goes in the table:

```
| Rationalization | Reality |
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after it works" | You won't. TDD catches design problems early. |
```

### Create Red Flags Lists

Make it easy for agents to self-check when rationalizing:

```
## Red Flags — STOP and Re-evaluate

- Code before test
- "I already manually tested it"
- "I'll just..."
- "Just this once"

**All of these mean: Delete code. Start over with proper process.**
```

## RED-GREEN-REFACTOR for Skills

### RED: Write Failing Test (Baseline)

Run pressure scenario with subagent WITHOUT the skill. Document exact behavior:
- What choices did they make?
- What rationalizations did they use (verbatim)?
- Which pressures triggered violations?

### GREEN: Write Minimal Skill

Write skill that addresses those specific rationalizations. Don't add extra content for hypothetical cases. Run same scenarios WITH skill. Agent should now comply.

### REFACTOR: Close Loopholes

Agent found new rationalization? Add explicit counter. Re-test until bulletproof.

## Token Efficiency

**Target word counts:**
- getting-started / bootstrap skills: <150 words each
- Frequently-loaded skills: <200 words total
- Other skills: <500 words

**Techniques:**
- Move detailed instructions to `references/` files (loaded on demand)
- Use cross-references between skills (describe intent, not mechanism)
- One excellent example beats many mediocre ones
- Choose the most relevant language for examples (don't port to 5+ languages)
- Compress verbose examples: show the pattern, not the narrative

## Common Rationalizations for Skipping Testing

| Excuse | Reality |
|--------|---------|
| "Skill is obviously clear" | Clear to you ≠ clear to other agents. Test it. |
| "It's just a reference" | References can have gaps. Test retrieval. |
| "Testing is overkill" | Untested skills have issues. Always. 15 min testing saves hours. |
| "I'll test if problems emerge" | Problems = agents can't use skill. Test BEFORE deploying. |
| "Too tedious to test" | Testing is less tedious than debugging bad skill in production. |
| "Academic review is enough" | Reading ≠ using. Test application scenarios. |
| "No time to test" | Deploying untested skill wastes more time fixing it later. |

**All of these mean: Test before deploying. No exceptions.**

## Skill Creation Checklist

### RED Phase — Write Failing Test
- [ ] Create pressure scenarios (3+ combined pressures for discipline skills)
- [ ] Run scenarios WITHOUT skill — document baseline behavior verbatim
- [ ] Identify patterns in rationalizations/failures

### GREEN Phase — Write Minimal Skill
- [ ] Name: `sw-` prefix, kebab-case, ≤100 characters, ASCII only
- [ ] Frontmatter: `name` + `description` only (no `allowed-tools` or other platform-specific fields)
- [ ] Description: ≤500 characters, starts with "Use when...", bilingual trigger keywords
- [ ] Description: triggering conditions ONLY, no workflow summary (CSO rule)
- [ ] Clear overview with core principle
- [ ] Address specific baseline failures from RED phase
- [ ] Keyword coverage for search (errors, symptoms, tools)
- [ ] One excellent example (not multi-language)
- [ ] Capabilities table routing to `references/` files
- [ ] Run scenarios WITH skill — verify agents now comply

### REFACTOR Phase — Close Loopholes
- [ ] Identify NEW rationalizations from testing
- [ ] Add explicit counters (if discipline skill)
- [ ] Build rationalization table from all test iterations
- [ ] Create red flags list
- [ ] Re-test until bulletproof

### Quality Checks
- [ ] All file references use relative paths from skill directory
- [ ] No cross-skill references (`../sw-xxx/`)
- [ ] No platform-specific variables (`${CLAUDE_PLUGIN_ROOT}` etc.)
- [ ] No platform-specific tool invocation names
- [ ] Common mistakes section with fixes
- [ ] No narrative storytelling

## Anti-Patterns

| Anti-Pattern | Why Bad | Fix |
|-------------|---------|-----|
| Narrative examples ("In session X, we found...") | Too specific, not reusable | Show the pattern, not the story |
| Multi-language examples (example-js.js, example-py.py, example-go.go) | Mediocre quality, maintenance burden | One excellent example in the most relevant language |
| Platform-specific tool names in skill body | Breaks on other platforms | Describe intent, not tool names |
| Workflow summary in description | Claude follows description, skips skill body | Description = triggering conditions only |
| Cross-skill file references (`../sw-xxx/references/`) | Breaks portability between platforms | Duplicate shared files into each skill directory |

## The Bottom Line

**Creating skills IS TDD for process documentation.**

Same Iron Law: No skill without failing test first.
Same cycle: RED (baseline) → GREEN (write skill) → REFACTOR (close loopholes).
Same benefits: Better quality, fewer surprises, bulletproof results.

If you follow TDD for code, follow it for skills. It's the same discipline applied to documentation.

## Integration

**Integrates with:**
- `sw-tdd-agent` — the TDD cycle this meta-skill adapts
- Harness skill template — the structure all Harness skills follow
- `AGENTS.md` Platform Feature Matrix — cross-platform compatibility rules
- `_context/config.yaml` — configuration-driven skill behavior
