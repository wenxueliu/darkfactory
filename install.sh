#!/usr/bin/env bash
# Harness Multiagents — One-Click Install Script
#
# Copies Agent skill files from the multiagents source tree to:
#   1. User-level  (~/.claude/skills/)     — global, all projects share
#   2. Project-level (<target>/skills/)     — scoped to one project
#
# Usage:  ./install.sh [OPTIONS]
#          ./install.sh --help

set -euo pipefail

# ---- constants ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_SKILLS="$SCRIPT_DIR/skills"
SOURCE_AGENTS="$SCRIPT_DIR/agents"
MINIMAL_SKILLS=("sw-controller" "sw-tdd-agent" "sw-reviewer-logic" "sw-worktree-controller")

# ---- defaults -----------------------------------------------------------
INSTALL_USER=false
TARGET_DIR=""
USE_MINIMAL=false
WITH_AGENTS=false
DRY_RUN=false
FORCE=false

# ---- helpers ------------------------------------------------------------
error()   { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
warn()    { printf 'WARN: %s\n' "$*" >&2; }
info()    { printf '  %s\n' "$*"; }
success() { printf 'SUCCESS: %s\n' "$*"; }

usage() {
    cat <<'HELPEOF'
install.sh — One-click Harness multi-agent skill installer

USAGE:
  install.sh [OPTIONS]

OPTIONS:
  --user              Install globally to ~/.claude/skills/
  --target <path>     Install into project directory (<path>/skills/)
  --minimal           Install only 4 essential skills (default: all)
  --with-agents       Also copy agents/*.md for Codex/OpenCode
  --dry-run           Preview what would happen; no changes
  --force             Skip confirmation prompt
  --help              Show this message

EXAMPLES:
  ./install.sh                                    # interactive prompt
  ./install.sh --user                             # global, all skills
  ./install.sh --user --minimal                   # global, 4 essentials
  ./install.sh --target /path/to/my-project       # project, all skills
  ./install.sh --target . --minimal --with-agents # project, minimal + agents
  ./install.sh --target /tmp/test --dry-run       # preview only

MINIMAL SKILLS (4):
  sw-controller          Top-level orchestrator
  sw-tdd-agent           TDD execution: RED -> GREEN -> REFACTOR
  sw-reviewer-logic      Logic review: correctness + edge cases
  sw-worktree-controller Single-task coordinator

FULL: all skill directories under skills/ (excluding reports/)
HELPEOF
    exit 0
}

# Cross-OS realpath — macOS does not ship realpath by default.
realpath_compat() {
    if command -v realpath &>/dev/null; then
        realpath "$1"
    elif command -v readlink &>/dev/null && readlink -f "$1" &>/dev/null 2>&1; then
        readlink -f "$1"
    else
        # POSIX fallback
        (cd "$(dirname "$1")" 2>/dev/null && echo "$PWD/$(basename "$1")")
    fi
}

detect_copy_cmd() {
    if command -v rsync &>/dev/null; then
        COPY_TOOL="rsync"
    else
        COPY_TOOL="cp"
        warn "rsync not found; falling back to cp -r"
    fi
}

# ---- argument parsing ---------------------------------------------------
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)       INSTALL_USER=true; shift ;;
            --target)     TARGET_DIR="$2"; shift 2 ;;
            --minimal)    USE_MINIMAL=true; shift ;;
            --with-agents) WITH_AGENTS=true; shift ;;
            --dry-run)    DRY_RUN=true; shift ;;
            --force)      FORCE=true; shift ;;
            --help|-h)    usage ;;
            *)            error "Unknown option: $1. Use --help for usage." ;;
        esac
    done
}

validate_args() {
    if $INSTALL_USER && [[ -n "$TARGET_DIR" ]]; then
        error "--user and --target are mutually exclusive."
    fi

    if [[ -n "$TARGET_DIR" ]]; then
        local resolved
        resolved="$(realpath_compat "$TARGET_DIR")" \
            || error "--target path '$TARGET_DIR' does not exist."
        TARGET_DIR="$resolved"
        [ -d "$TARGET_DIR" ] || error "--target '$TARGET_DIR' is not a directory."
    fi

    [ -d "$SOURCE_SKILLS" ] || error "Source skills/ not found at $SOURCE_SKILLS"

    if $WITH_AGENTS; then
        [ -d "$SOURCE_AGENTS" ] || error "Source agents/ not found at $SOURCE_AGENTS. Omit --with-agents."
    fi
}

# ---- interactive prompt -------------------------------------------------
interactive_prompt() {
    if $INSTALL_USER || [[ -n "$TARGET_DIR" ]]; then
        return 0
    fi

    echo ""
    echo "  How would you like to install the Harness skills?"
    echo ""
    echo "    1) User-level (global)  ->  ~/.claude/skills/"
    echo "    2) Project-level        ->  <target>/skills/"
    echo ""
    printf '  Enter 1 or 2 (Ctrl-C to cancel): '
    read -r choice
    case "$choice" in
        1) INSTALL_USER=true ;;
        2)
            printf '  Enter project path: '
            read -r TARGET_DIR
            local resolved
            resolved="$(realpath_compat "$TARGET_DIR")" \
                || error "Path does not exist: $TARGET_DIR"
            TARGET_DIR="$resolved"
            [ -d "$TARGET_DIR" ] || error "Not a directory: $TARGET_DIR"
            ;;
        *) error "Invalid choice. Exiting." ;;
    esac
}

# ---- skill discovery ----------------------------------------------------
# Returns newline-separated list of skill directory names.
get_skill_list() {
    local skills=""
    while IFS= read -r dirname; do
        skills="${skills}${dirname}
"
    done < <(find "$SOURCE_SKILLS" -maxdepth 1 -type d \
        -not -path "$SOURCE_SKILLS" \
        -not -name "reports" \
        -printf "%f\n" | sort)
    # trim trailing newline
    skills="${skills%$'\n'}"

    if $USE_MINIMAL; then
        local filtered=""
        for ms in "${MINIMAL_SKILLS[@]}"; do
            if printf '%s\n' "$skills" | grep -qxF "$ms"; then
                filtered="${filtered}${ms}
"
            else
                warn "Minimal skill '$ms' not found in source; skipping."
            fi
        done
        skills="${filtered%$'\n'}"
    fi

    printf '%s\n' "$skills"
}

# ---- confirmation -------------------------------------------------------
count_skills() {
    local skills
    skills="$(get_skill_list)"
    if [ -z "$skills" ]; then
        echo 0
    else
        printf '%s\n' "$skills" | grep -c '^'
    fi
}

confirm_or_exit() {
    if $FORCE || $DRY_RUN; then
        return 0
    fi

    local count
    count=$(count_skills)

    echo ""
    echo "  Will install $count skills to: $TARGET_SKILLS"
    if $WITH_AGENTS; then
        echo "  Will also install agent templates to: $TARGET_AGENTS"
    fi
    echo ""
    printf '  Proceed? [y/N] '
    read -r confirm
    case "$confirm" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) echo "  Cancelled."; exit 0 ;;
    esac
}

# ---- dry-run wrapper ----------------------------------------------------
dry_or_real() {
    if $DRY_RUN; then
        printf '[DRY-RUN] %s\n' "$*"
    else
        eval "$@"
    fi
}

# ---- resolve target paths -----------------------------------------------
resolve_target_paths() {
    if $INSTALL_USER; then
        TARGET_SKILLS="$HOME/.claude/skills"
        TARGET_AGENTS="$HOME/.agents/skills"
    else
        TARGET_SKILLS="$TARGET_DIR/skills"
        TARGET_AGENTS="$TARGET_DIR/.agents/skills"
    fi
}

# ---- install skills -----------------------------------------------------
install_skills() {
    local skill_list dest_skills
    skill_list="$(get_skill_list)"
    dest_skills="$TARGET_SKILLS"

    dry_or_real "mkdir -p \"$dest_skills\""

    local count=0
    while IFS= read -r skill_name; do
        [ -z "$skill_name" ] && continue
        local src="$SOURCE_SKILLS/$skill_name"
        local dst="$dest_skills/$skill_name"

        if $DRY_RUN; then
            info "  $skill_name -> $dst/"
        else
            info "  $skill_name ..."
            if [ "$COPY_TOOL" = "rsync" ]; then
                # --delete ensures stale files are removed on re-install
                rsync -a --delete "$src/" "$dst/"
            else
                rm -rf "$dst"
                cp -r "$src" "$dst"
            fi
        fi
        count=$((count + 1))
    done <<ENDOFSKILLS
$skill_list
ENDOFSKILLS

    success "Installed $count skill(s) to $dest_skills"
}

# ---- install agents -----------------------------------------------------
install_agents() {
    $WITH_AGENTS || return 0

    local dest_agents="$TARGET_AGENTS"
    dry_or_real "mkdir -p \"$dest_agents\""

    local count=0
    for agent_file in "$SOURCE_AGENTS"/*.md; do
        [ -f "$agent_file" ] || continue
        local bn
        bn="$(basename "$agent_file")"

        if $DRY_RUN; then
            info "  $bn -> $dest_agents/"
        else
            info "  $bn ..."
            if [ "$COPY_TOOL" = "rsync" ]; then
                rsync -a "$agent_file" "$dest_agents/"
            else
                cp "$agent_file" "$dest_agents/"
            fi
        fi
        count=$((count + 1))
    done

    success "Installed $count agent template(s) to $dest_agents"
}

# ---- summary ------------------------------------------------------------
print_summary() {
    if $DRY_RUN; then
        echo ""
        echo "============================================"
        echo "  DRY-RUN complete (no changes made)."
        echo "  Re-run without --dry-run to install."
        echo "============================================"
        return 0
    fi

    echo ""
    echo "============================================"
    echo "  Installation complete"
    echo "============================================"
    echo "  Skills:           $TARGET_SKILLS"
    if $WITH_AGENTS; then
        echo "  Agent templates:  $TARGET_AGENTS"
    fi
    echo ""
    echo "  To start using Harness:"
    echo "    Claude Code:  /sw-controller <your request>"
    echo "    Codex:        sw-controller              (after restart)"
    echo "    OpenCode:     skill tool: sw-controller  (after restart)"
    echo ""
    echo "  Tip: re-run this script anytime to update to the latest skills."
    echo "============================================"
}

# ---- main ---------------------------------------------------------------
main() {
    parse_args "$@"
    validate_args
    detect_copy_cmd
    interactive_prompt
    resolve_target_paths
    confirm_or_exit

    echo ""
    echo "=== Installing Harness Multi-Agent Skills ==="
    echo ""

    install_skills
    install_agents
    print_summary
}

main "$@"
