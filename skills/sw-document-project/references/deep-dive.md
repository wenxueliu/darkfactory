# Deep-Dive Documentation Workflow

Exhaustive deep-dive documentation of specific project areas. Always uses exhaustive scan level.

## Critical Rules

- **Literal full-file review REQUIRED.** Sampling, guessing, or relying solely on tooling output is FORBIDDEN.
- **Read every line of every file in scope.** Capture plain-language explanations that future developer agents can act on.
- **Write-as-you-go.** Write findings immediately, purge details from context.
- **Communication**: Communicate in `{communication_language}`. Write all documents in `{document_output_language}`.

---

## Step D1: Identify Area for Deep-Dive

Load existing project structure from `{project_knowledge}/index.md` and `project-parts.json` (if exists).
Load source tree analysis to understand available areas.

Ask user:

> What area would you like to deep-dive into?
>
> **Suggested Areas Based on Project Structure:**
>
> {if has_api_routes:}
> ## API Routes ({count} endpoints found)
> {list api route groups with endpoint counts and paths}
>
> {if has_feature_modules:}
> ## Feature Modules ({count} features)
> {list feature modules with file counts and paths}
>
> {if has_ui_components:}
> ## UI Component Areas
> {list component groups with counts and paths}
>
> {if has_services:}
> ## Services/Business Logic
> {list service groups with paths}
>
> **Or specify custom:**
> - Folder path (e.g., "client/src/features/dashboard")
> - File path (e.g., "server/src/api/users.ts")
> - Feature name (e.g., "authentication system")

Parse user input to determine:
- `target_type`: "folder" | "file" | "feature" | "api_group" | "component_group"
- `target_path`: absolute path to scan
- `target_name`: human-readable name for documentation
- `target_scope`: list of all files to analyze

Display confirmation:
> Target: {target_name}
> Type: {target_type}
> Path: {target_path}
> Estimated files to analyze: {estimated_count}
>
> This will read EVERY file in this area. Proceed? [y/n]

If user says no, return to area selection.

---

## Step D2: Comprehensive Exhaustive Scan of Target Area

Initialize `file_inventory = []`.

### By target type:

**Folder:**
- Get complete recursive file list from target_path
- Filter out: node_modules/, .git/, dist/, build/, coverage/, *.min.js, *.map
- For EVERY remaining file:
  - Read complete file contents (all lines)
  - Extract all exports (functions, classes, types, interfaces, constants) with signatures
  - Extract all imports (dependencies)
  - Identify purpose from comments and code structure
  - Write 1-2 sentences (minimum) describing behaviour, side effects, assumptions
  - Extract function signatures with parameter types and return types
  - Note any TODOs, FIXMEs, comments
  - Identify patterns (hooks, components, services, controllers, etc.)
  - Capture per-file: `contributor_note`, `risks`, `verification_steps`, `suggested_tests`
  - Store in file_inventory

**File:**
- Read complete file at target_path
- Extract all information as above
- Read all files it imports (follow import chain 1 level deep)
- Find all files that import this file (dependents via grep/search)
- Store all in file_inventory

**API Group:**
- Identify all route/controller files in API group
- Read all route handlers completely
- Read associated middleware, controllers, services
- Read data models and schemas used
- Extract complete request/response schemas
- Document authentication and authorization requirements
- Store all in file_inventory

**Feature:**
- Search codebase for all files related to feature name
- Include: UI components, API endpoints, models, services, tests
- Read each file completely
- Store all in file_inventory

**Component Group:**
- Get all component files in group
- Read each component completely
- Extract: Props interfaces, hooks used, child components, state management
- Store all in file_inventory

### Per-file documentation

For each file in `file_inventory`, document:
- **File Path**: Full path
- **Purpose**: What this file does (1-2 sentences)
- **Lines of Code**: Total LOC
- **Exports**: Complete list with signatures (functions, classes, types, constants)
- **Imports/Dependencies**: What it uses and why
- **Used By**: Files that import this (dependents)
- **Key Implementation Details**: Important logic, algorithms, patterns
- **State Management**: If applicable (Redux, Context, local state)
- **Side Effects**: API calls, database queries, file I/O, external services
- **Error Handling**: Try/catch blocks, error boundaries, validation
- **Testing**: Associated test files and coverage
- **Comments/TODOs**: Any inline documentation or planned work

---

## Step D3: Analyze Relationships and Data Flow

Build dependency graph for scanned area:
- Create graph with files as nodes
- Add edges for import relationships
- Identify circular dependencies if any
- Find entry points (files not imported by others in scope)
- Find leaf nodes (files that don't import others in scope)

Trace data flow through the system:
- Follow function calls and data transformations
- Track API calls and their responses
- Document state updates and propagation
- Map database queries and mutations

Identify integration points:
- External APIs consumed
- Internal APIs/services called
- Shared state accessed
- Events published/subscribed
- Database tables accessed

---

## Step D4: Find Related Code and Similar Patterns

Search codebase OUTSIDE scanned area for:
- Similar file/folder naming patterns
- Similar function signatures and component structures
- Similar API patterns
- Reusable utilities that could be used

Identify code reuse opportunities:
- Shared utilities available
- Design patterns used elsewhere
- Component libraries available
- Helper functions that could apply

Find reference implementations:
- Similar features in other parts of codebase
- Established patterns to follow
- Testing approaches used elsewhere

---

## Step D5: Generate Comprehensive Deep-Dive Documentation

Create documentation filename: `deep-dive-{sanitized_target_name}.md`.

Aggregate contributor insights across files:
- Combine unique risk/gotcha notes into `risks_notes`
- Combine verification steps into `verification_steps`
- Combine recommended test commands into `suggested_tests`

Load template from `templates/deep-dive-template.md`.
Fill template with all collected data from Steps D2-D4.
Write filled template to: `{project_knowledge}/deep-dive-{sanitized_target_name}.md`.
Validate deep-dive document completeness.

---

## Step D6: Update Master Index with Deep-Dive Link

Read existing `index.md`.

Check if "Deep-Dive Documentation" section exists. If not, add after "Generated Documentation":
```
## Deep-Dive Documentation

Detailed exhaustive analysis of specific areas:
```

Add link to new deep-dive doc:
```
- [{target_name} Deep-Dive](./deep-dive-{sanitized_target_name}.md) - Comprehensive analysis of {target_description} ({file_count} files, {total_loc} LOC) - Generated {date}
```

Update index metadata (Last Updated date, Deep-Dives count).
Save updated index.md.

---

## Step D7: Offer to Continue or Complete

Display summary:

> ## Deep-Dive Documentation Complete!
>
> **Generated:** {project_knowledge}/deep-dive-{target_name}.md
> **Files Analyzed:** {file_count}
> **Lines of Code Scanned:** {total_loc}
>
> **Documentation Includes:**
> - Complete file inventory with all exports
> - Dependency graph and data flow
> - Integration points and API contracts
> - Testing analysis and coverage
> - Related code and reuse opportunities
> - Implementation guidance
>
> **Index Updated:** index.md now includes link to this deep-dive

Ask user:

> Would you like to:
> 1. **Deep-dive another area** — Analyze another feature/module/folder
> 2. **Finish** — Complete workflow

If choice 1: Clear current deep_dive_target, go to Step D1 (select new area).
If choice 2: Display final message with master index location and all deep-dives generated. Exit workflow.
