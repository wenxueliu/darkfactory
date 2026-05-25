# Full Project Scan Workflow

Complete project documentation (initial scan or full rescan). 12-step workflow.

## Critical Rules

- **Write-as-you-go**: Each document written to disk IMMEDIATELY after generation. After writing, purge detailed findings from context — keep only 1-2 sentence summaries.
- **Batching**: For deep/exhaustive scans, process one subfolder at a time: read -> extract -> write -> validate -> purge -> next.
- **No hallucination**: Only document what actually exists. Never invent files, APIs, or patterns.
- **Communication**: Communicate in `{communication_language}`. Write all documents in `{document_output_language}`.

---

## Step 0.5: Load Documentation Requirements

Load `documentation-requirements.csv` from the skill root. Store all 12 rows indexed by `project_type_id` for project detection and requirements lookup.

The CSV contains:
- 12 project types (web, mobile, backend, cli, library, desktop, game, data, extension, infra, embedded)
- Detection columns: `key_file_patterns` (used to identify project type)
- Requirement columns: `requires_api_scan`, `requires_data_models`, etc.
- Pattern columns: `critical_directories`, `test_file_patterns`, etc.

Display: "Loaded documentation requirements for 12 project types."

---

## Step 1: Detect Project Structure and Classify Project Type

Ask user: "What is the root directory of the project to document?" (default: current working directory). Store as `project_root_path`.

Scan `project_root_path` for key indicators:
- Directory structure (presence of client/, server/, api/, src/, app/, etc.)
- Key files (package.json, go.mod, requirements.txt, etc.)

Detect if project is:
- **Monolith**: Single cohesive codebase
- **Monorepo**: Multiple parts in one repository
- **Multi-part**: Separate client/server or similar architecture

If multiple distinct parts detected (e.g., client/ and server/ folders):
- List detected parts with their paths
- Ask user to confirm: "I detected multiple parts in this project. Is this correct? Should I document each part separately?"
- If confirmed: For each part, identify root path, run project type detection using `key_file_patterns` from CSV

If single cohesive project detected:
- Set `repository_type = "monolith"`
- Create single part with `root_path = project_root_path`

For each part, match detected technologies/file patterns against `key_file_patterns` column in CSV. Assign `project_type_id` to each part. Load corresponding documentation requirements row.

Present classification to user: "I've classified this project: {summary}. Does this look correct?"

Purge detailed scan results from context. Keep only: "{repository_type}, {parts_count} parts, {primary_tech}".

---

## Step 2: Discover Existing Documentation and Gather User Context

For each part, scan for existing documentation using patterns:
- README.md, README.rst, README.txt
- CONTRIBUTING.md, CONTRIBUTING.rst
- ARCHITECTURE.md, docs/architecture/
- DEPLOYMENT.md, docs/deployment/
- API.md, docs/api/
- Any files in docs/, documentation/, .github/ folders

Create inventory of existing_docs with: file path, file type, which part it belongs to (if multi-part).

Ask user: "I found these existing documentation files: {list}. Are there any other important documents or key areas I should focus on? [Provide paths or guidance, or type 'none']"

Store user guidance as `user_context`.

Purge detailed doc contents from context. Keep only: "{count} docs found".

---

## Step 3: Analyze Technology Stack for Each Part

For each part:
- Load `key_file_patterns` from documentation requirements
- Scan part root for these patterns
- Parse technology manifest files (package.json, go.mod, requirements.txt, etc.)
- Extract: framework, language, version, database, dependencies
- Build technology table with columns: Category, Technology, Version, Justification

Determine architecture pattern based on detected tech stack:
- Use `project_type_id` as primary indicator (e.g., "web" -> layered/component-based, "backend" -> service/API-centric)
- Consider framework patterns (e.g., React -> component hierarchy, Express -> middleware pipeline)
- Store as `architecture_pattern` for each part

Purge detailed tech analysis from context. Keep only: "{framework} on {language}".

---

## Step 4: Perform Conditional Analysis Based on Project Type Requirements

### Batching Strategy (deep/exhaustive scans only)

For `scan_level == deep`: Use `critical_directories` from documentation requirements.
For `scan_level == exhaustive`: Get ALL subfolders recursively (excluding node_modules, .git, dist, build, coverage).

For each subfolder:
1. Read all files in subfolder (use judgment for files >5000 LOC)
2. Extract required information based on conditional flags below
3. IMMEDIATELY write findings to appropriate output file
4. Validate written document (section-level validation)
5. Purge detailed findings from context (keep only 1-2 sentence summary)
6. Move to next subfolder

For `scan_level == quick`: Use pattern matching only — do NOT read source files. Use glob/grep to identify file locations and patterns from filenames, directory structure, and config files only.

### Conditional checks

For each part, check documentation_requirements boolean flags:

**If `requires_api_scan == true`:**
- Scan for API routes/endpoints using `integration_scan_patterns`
- Look for: controllers/, routes/, api/, handlers/, endpoints/
- Quick: use glob to find route files, extract patterns from filenames
- Deep/exhaustive: read files in batches, extract HTTP methods, paths, request/response types
- Build API contracts catalog
- Write to: `{project_knowledge}/api-contracts-{part_id}.md`
- Purge: keep only "{count} endpoints documented"

**If `requires_data_models == true`:**
- Scan for data models using `schema_migration_patterns`
- Look for: models/, schemas/, entities/, migrations/, prisma/, ORM configs
- Quick: identify schema files via glob, parse migration file names
- Deep/exhaustive: read model files in batches, extract table names, fields, relationships
- Build database schema documentation
- Write to: `{project_knowledge}/data-models-{part_id}.md`
- Purge: keep only "{count} tables documented"

**If `requires_state_management == true`:**
- Analyze state management patterns (Redux, Context API, MobX, Vuex, Pinia, Provider)
- Identify: stores, reducers, actions, state structure

**If `requires_ui_components == true`:**
- Inventory UI component library
- Scan: components/, ui/, widgets/, views/ folders
- Categorize: Layout, Form, Display, Navigation, etc.
- Identify: design system, component patterns, reusable elements

**If `requires_hardware_docs == true`:**
- Look for hardware schematics using `hardware_interface_patterns`
- Ask user if they have pinout diagrams, schematics, PCB layouts

**If `requires_asset_inventory == true`:**
- Scan and catalog assets using `asset_patterns`
- Categorize by: Images, Audio, 3D Models, Sprites, Textures
- Calculate: total size, file counts, formats used

**Additional pattern scans** (apply scan_level strategy):
- `config_patterns` — Configuration management
- `auth_security_patterns` — Authentication/authorization approach
- `entry_point_patterns` — Application entry points and bootstrap
- `shared_code_patterns` — Shared libraries and utilities
- `async_event_patterns` — Event-driven architecture
- `ci_cd_patterns` — CI/CD pipeline details
- `localization_patterns` — i18n/l10n support

Purge all detailed scan results. Keep only summaries: "APIs: {count} endpoints", "Data: {count} tables", "Components: {count} components".

---

## Step 5: Generate Source Tree Analysis

For each part, generate complete directory tree using `critical_directories` from doc requirements.

Annotate the tree with:
- Purpose of each critical directory
- Entry points marked
- Key file locations highlighted
- Integration points noted (for multi-part projects)

Create formatted source tree with descriptions. Example:
```
project-root/
├── client/          # React frontend (Part: client)
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Route-based pages
│   │   └── api/         # API client layer -> Calls server/
├── server/          # Express API backend (Part: api)
│   ├── src/
│   │   ├── routes/      # REST API endpoints
│   │   ├── models/      # Database models
│   │   └── services/    # Business logic
```

IMMEDIATELY write `source-tree-analysis.md` using `templates/source-tree-template.md`. Validate structure. Purge: "Source tree with {count} critical folders".

---

## Step 6: Extract Development and Operational Information

Scan for development setup using key_file_patterns and existing docs:
- Prerequisites (Node version, Python version, etc.)
- Installation steps (npm install, pip install, etc.)
- Environment setup (.env files, config)
- Build commands (npm run build, make, etc.)
- Run commands (npm start, go run, etc.)
- Test commands using `test_file_patterns`

Look for deployment configuration using `ci_cd_patterns`:
- Dockerfile, docker-compose.yml
- Kubernetes configs (k8s/, helm/)
- CI/CD pipelines (.github/workflows/, .gitlab-ci.yml)
- Deployment scripts
- Infrastructure as Code (terraform/, pulumi/)

If CONTRIBUTING.md or similar found: extract contribution guidelines (code style, PR process, commit conventions, testing requirements).

Purge: "Dev setup and deployment documented".

---

## Step 7: Detect Multi-Part Integration Architecture

Only if project has multiple parts.

Analyze how parts communicate:
- Scan `integration_scan_patterns` across parts
- Identify: REST calls, GraphQL queries, gRPC, message queues, shared databases
- Document: API contracts between parts, data flow, authentication flow

Create integration_points array with: from (source part), to (target part), type (REST API, GraphQL, gRPC, Event Bus), details (endpoints, protocols, data formats).

IMMEDIATELY write `integration-architecture.md`. Validate. Purge: "{count} integration points".

---

## Step 8: Generate Architecture Documentation for Each Part

For each part:
- Fill all sections with discovered information:
  - Executive Summary
  - Technology Stack (from Step 3)
  - Architecture Pattern
  - Data Architecture (from Step 4 data models scan)
  - API Design (from Step 4 API scan if applicable)
  - Component Overview (from Step 4 component scan if applicable)
  - Source Tree (from Step 5)
  - Development Workflow (from Step 6)
  - Deployment Architecture (from Step 6)
  - Testing Strategy (from test patterns)

If single part: generate `architecture.md` (no part suffix).
If multi-part: generate `architecture-{part_id}.md` for each part.

For each architecture file: write immediately, validate, purge. Keep only: "Architecture for {part_id} written".

---

## Step 9: Generate Supporting Documentation Files

Generate **project-overview.md** using `templates/project-overview-template.md` with:
- Project name and purpose (from README or user input)
- Executive summary, tech stack summary table
- Architecture type classification
- Repository structure (monolith/monorepo/multi-part)
- Links to detailed docs

Generate **component-inventory.md** (or per-part) with:
- All discovered components from Step 4
- Categorized by type (Layout, Form, Display, Navigation, etc.)
- Reusable vs specific components
- Design system elements (if found)

Generate **development-guide.md** (or per-part) with:
- Prerequisites and dependencies
- Environment setup instructions
- Local development commands, build process, testing approach

If deployment configuration found: generate **deployment-guide.md**.
If contribution guidelines found: generate **contribution-guide.md**.
If API contracts documented: generate **api-contracts.md** (or per-part).
If data models documented: generate **data-models.md** (or per-part).
If multi-part: generate **integration-architecture.md** and **project-parts.json**.

Write each file immediately after generation. Validate each file. Purge after writing.

---

## Step 10: Generate Master Index

Create `index.md` using `templates/index-template.md` as the primary AI retrieval entry point.

**Incomplete documentation marker convention**: When a document SHOULD be generated but wasn't (due to quick scan or missing data), use EXACTLY this marker: `(To be generated)` at the end of the markdown link line.
Example: `- [API Contracts - Server](./api-contracts-server.md) (To be generated)`

Before writing index.md, check which expected files actually exist on disk. Set existence flags for each document type. Track missing files.

Include:
- Project name and type
- Quick reference (tech stack, architecture type)
- Links to all generated docs (with `(To be generated)` markers for missing)
- Links to discovered existing docs
- Getting started section
- AI-assisted development guidance (which docs to reference for UI-only, API/backend, full-stack, deployment)

For multi-part projects: include part-based navigation, cross-part integration links, getting started per part.

Write immediately. Validate. Purge: "Master index generated".

---

## Step 11: Validate and Review Generated Documentation

Show summary of all generated files:
```
Generated in {project_knowledge}/:
{file_list_with_sizes}
```

Run validation against `references/checklist.md`.

### Incomplete Documentation Detection

Scan index.md for:
1. Exact marker: `(To be generated)` (case-sensitive)
2. Fallback fuzzy markers: `(TBD)`, `(TODO)`, `(Coming soon)`, `(Not yet generated)`, `(Pending)`

For each match, extract: document title, file path, doc type, part ID (if applicable).

Present summary to user:

> Documentation generation complete!
>
> Summary:
> - Project Type: {summary}
> - Parts Documented: {count}
> - Files Generated: {count}
>
> {if incomplete docs found:}
> Incomplete Documentation Detected: {count} item(s) marked as incomplete.
>
> Would you like to:
> 1. **Generate incomplete documentation** — Complete any of the {count} items
> 2. Review any specific section [type section name]
> 3. Add more detail to any area [type area name]
> 4. Generate additional custom documentation [describe what]
> 5. Finalize and complete [type 'done']

If user selects option 1:
- Ask which items to generate (by number, comma-separated, or 'all')
- For each selected item, re-run the appropriate step (Step 4 for API/data, Step 8 for architecture, Step 9 for other docs)
- After generation, update index.md to remove markers
- Loop back to re-scan for remaining incomplete items

If user requests other changes (options 2-3): make requested modifications, regenerate affected files.
If user selects finalize (option 4-5): proceed to Step 12.

---

## Step 12: Finalize and Provide Next Steps

Display completion message:

> ## Project Documentation Complete!
>
> **Location:** {project_knowledge}/
> **Master Index:** {project_knowledge}/index.md (primary entry point for AI-assisted development)
>
> **Generated Documentation:**
> {files_list}
>
> **Next Steps:**
> 1. Review the index.md to familiarize yourself with the documentation structure
> 2. For UI-only features: Reference architecture + component inventory docs
> 3. For API-only features: Reference architecture + API contracts docs
> 4. For full-stack features: Reference all architecture docs (+ integration docs if multi-part)
>
> **Verification Recap:**
> - Tests/extractions executed: {summary}
> - Outstanding risks or follow-ups: {risks}
> - Recommended next checks: {checks}

Workflow complete.
