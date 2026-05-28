# Workflow Router

This document determines the workflow mode and delegates to the appropriate sub-workflow.

## On Activation

Load config from `{project-root}/_context/config.yaml` and resolve:
- `communication_language` — language for all communication
- `document_output_language` — language for output documents
- `project_knowledge` — output location for generated docs (default: `_context-output/project-docs/`)

You MUST communicate in `{communication_language}` and write all documents in `{document_output_language}`.

---

## Step 1: Check for Existing Documentation

Check if `{project_knowledge}/index.md` exists.

### If index.md exists

Read existing index.md to extract metadata (date, project structure, parts count). Store as `existing_doc_date` and `existing_structure`.

Ask the user:

> I found existing documentation generated on {existing_doc_date}.
>
> What would you like to do?
>
> 1. **Re-scan entire project** — Update all documentation with latest changes
> 2. **Deep-dive into specific area** — Generate detailed documentation for a particular feature/module/folder
> 3. **Cancel** — Keep existing documentation as-is

- If choice 1: Set `workflow_mode = "full_rescan"`, proceed to Step 2.
- If choice 2: Set `workflow_mode = "deep_dive"`, set `scan_level = "exhaustive"`, load `references/deep-dive.md`.
- If choice 3: Exit workflow.

### If index.md does not exist

Set `workflow_mode = "initial_scan"`. Display: "No existing documentation found. Starting initial project scan..."

Proceed to Step 2.

---

## Step 2: Select Scan Level

Only applicable if `workflow_mode != "deep_dive"`.

Ask the user:

> Choose your scan depth level:
>
> **1. Quick Scan** (2-5 minutes) [DEFAULT]
> - Pattern-based analysis without reading source files
> - Scans: config files, package manifests, directory structure
> - Best for: quick project overview, initial understanding
> - File reading: minimal (configs, README, package.json, etc.)
>
> **2. Deep Scan** (10-30 minutes)
> - Reads files in critical directories based on project type
> - Scans: all critical paths from documentation requirements
> - Best for: comprehensive documentation for development
> - File reading: selective (key files in critical directories)
>
> **3. Exhaustive Scan** (30-120 minutes)
> - Reads ALL source files in project
> - Scans: every source file (excludes node_modules, dist, build)
> - Best for: complete analysis, migration planning, detailed audit
> - File reading: complete (all source files)

- If choice 1 or default: Set `scan_level = "quick"`.
- If choice 2: Set `scan_level = "deep"`.
- If choice 3: Set `scan_level = "exhaustive"`.

---

## Delegation

Now load and follow one of:

- **Full Scan**: `references/full-scan.md` — 12-step complete project documentation
- **Deep Dive**: `references/deep-dive.md` — exhaustive area-specific analysis
