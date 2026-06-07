---
name: case-library
description: Case library of common rationalizations and anti-patterns observed when authoring skills. Use during REFACTOR phase to identify new rationalizations that need explicit counters. Use when reviewing existing skills for known anti-patterns.
---

# Skill Authoring Case Library

Real patterns observed in baseline testing. Each entry is a recurring failure mode that the corresponding counter addresses.

---

## A. Common Rationalizations for Skipping Testing

| Excuse | Reality |
|--------|---------|
| "Skill is obviously clear" | Clear to you ≠ clear to other agents. Test it. |
| "It's just a reference" | References can have gaps. Test retrieval. |
| "Testing is overkill" | Untested skills have issues. Always. 15 min testing saves hours. |
| "I'll test if problems emerge" | Problems = agents can't use skill. Test BEFORE deploying. |
| "Too tedious to test" | Testing is less tedious than debugging bad skill in production. |
| "Academic review is enough" | Reading ≠ using. Test application scenarios. |
| "No time to test" | Deploying untested skill wastes more time fixing it later. |

**All of these mean:** Test before deploying. No exceptions.

---

## B. Common Rationalizations for Skipping the Iron Law

| Excuse | Reality |
|--------|---------|
| "Skill is simple, don't need process" | Simple skills have gaps too. Process is fast for simple skills. |
| "Emergency, no time for testing" | Systematic testing is FASTER than guess-and-check thrashing. |
| "Just try this first, then test" | First version sets the pattern. Do it right from the start. |
| "I'll write tests after confirming skill works" | Untested skills don't stick. Test first proves it. |
| "Multiple changes at once saves time" | Can't isolate what worked. Causes new loopholes. |
| "Reference too long, I'll adapt" | Partial understanding guarantees loopholes. Read it completely. |
| "I see the problem, let me fix" | Seeing symptoms ≠ understanding root cause. |

**All of these mean:** Follow RED → GREEN → REFACTOR. No exceptions.

---

## C. Common Anti-Patterns in Skills

| Anti-Pattern | Why Bad | Fix |
|--------------|---------|-----|
| Narrative examples ("In session X, we found...") | Too specific, not reusable | Show the pattern, not the story |
| Multi-language examples (example-js.js, example-py.py, example-go.go) | Mediocre quality, maintenance burden | One excellent example in the most relevant language |
| Platform-specific tool names in skill body | Breaks on other platforms | Describe intent, not tool names |
| Workflow summary in description | Claude follows description, skips skill body | Description = triggering conditions only |
| Cross-skill file references (`../sw-xxx/references/`) | Breaks portability between platforms | Duplicate shared files into each skill directory |

---

## D. The Spirit vs Letter Loophole

**Pattern observed in baseline testing:**

> "The skill says don't write code before test. I didn't write code before test — I wrote a script. Scripts aren't code."

**Counter to add to any discipline-enforcing skill:**

```markdown
**Violating the letter of the rules is violating the spirit of the rules.**

This cuts off the entire class of "I'm following the spirit" rationalizations.
```

---

## E. The "Just This Once" Pattern

**Pattern observed in baseline testing:**

> "I know I should test, but this is a one-line edit. Just this once."

**Counter to add:**

```markdown
**No exceptions:**
- Not for "simple additions"
- Not for "just adding a section"
- Not for "documentation updates"
- Don't keep untested changes as "reference"
- Don't "adapt" while running tests
- Delete means delete
```

---

## F. The Adaptation Loophole

**Pattern observed:**

> "Pattern says X but I'll adapt it differently because the situation is special."

**Counter:**

```markdown
Pattern says X? Apply X. "Adapting" without testing = loophole hunting.
```

---

## G. Real Refactor Cycle Example

| Iteration | Rationalization Caught | Counter Added |
|-----------|------------------------|---------------|
| 1 | "I already manually tested" | Add "Manual testing ≠ automated test" |
| 2 | "Just this once for a small change" | Add "No exceptions" section |
| 3 | "I adapted the pattern for this case" | Add "Adaptation without test = loophole" |
| 4 | "Tests pass for happy path, that's enough" | Add "Edge cases required" section |
| 5 | "The user already approved this design" | Add "Approval ≠ tested behavior" |

**This is a 5-round refactor cycle.** Real skills often need 3-5 rounds to become bulletproof.

---

## See Also

- `SKILL.md` → Iron Law section
- `SKILL.md` → RED-GREEN-REFACTOR for Skills
- `SKILL.md` → Skill Creation Checklist
