/**
 * Harness plugin for OpenCode.ai
 *
 * Injects Harness bootstrap context via user message transform.
 * Auto-registers skills directory via config hook (no symlinks needed).
 * Adapts the Superpowers OpenCode plugin pattern for the Harness multi-agent system.
 */

import path from 'path';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Simple frontmatter extraction (avoid dependency on skills-core for bootstrap)
const extractAndStripFrontmatter = (content) => {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { frontmatter: {}, content };

  const frontmatterStr = match[1];
  const body = match[2];
  const frontmatter = {};

  for (const line of frontmatterStr.split('\n')) {
    const colonIdx = line.indexOf(':');
    if (colonIdx > 0) {
      const key = line.slice(0, colonIdx).trim();
      const value = line.slice(colonIdx + 1).trim().replace(/^["']|["']$/g, '');
      frontmatter[key] = value;
    }
  }

  return { frontmatter, content: body };
};

export const HarnessPlugin = async ({ client, directory }) => {
  const homeDir = os.homedir();
  const harnessSkillsDir = path.resolve(__dirname, '../../skills');

  // Helper to generate bootstrap content
  const getBootstrapContent = () => {
    // Try to load using-harness skill (the bootstrap skill)
    const skillPath = path.join(harnessSkillsDir, 'using-harness', 'SKILL.md');
    if (!fs.existsSync(skillPath)) {
      // Fallback: inject a minimal bootstrap without the full skill
      return `<EXTREMELY_IMPORTANT>
You are running the Harness multi-agent system.

Harness provides a complete software development methodology with specialized agents:
- hw-controller: Top-level orchestrator (requirements → design → execution → delivery)
- hw-tdd-agent: TDD practitioner (RED→GREEN→REFACTOR)
- hw-reviewer-logic: Logic and correctness review
- hw-reviewer-security: Security vulnerability review
- hw-reviewer-performance: Performance and scalability review
- hw-worktree-controller: Single-task execution coordinator

Use the skill tool to list and load available Harness skills. The AGENTS.md file contains
the full platform-agnostic working agreement.

**Tool Mapping for OpenCode:**
When skills reference tools you don't have, substitute OpenCode equivalents:
- TodoWrite → todowrite
- Agent tool with subagents → Use OpenCode's subagent system (@mention)
- Skill tool → OpenCode's native skill tool
- Read, Write, Edit, Bash → Your native tools

Follow the TDD iron law: no production code without a failing test first.
Human judgment is the ultimate backstop on strategic decisions.
</EXTREMELY_IMPORTANT>`;
    }

    const fullContent = fs.readFileSync(skillPath, 'utf8');
    const { content } = extractAndStripFrontmatter(fullContent);

    const toolMapping = `**Tool Mapping for OpenCode:**
When skills reference tools you don't have, substitute OpenCode equivalents:
- TodoWrite → todowrite
- Agent tool with subagents → Use OpenCode's subagent system (@mention)
- Skill tool → OpenCode's native skill tool
- Read, Write, Edit, Bash → Your native tools

Use OpenCode's native skill tool to list and load skills.`;

    return `<EXTREMELY_IMPORTANT>
You are running the Harness multi-agent system.

**IMPORTANT: The using-harness skill content is included below. It is ALREADY LOADED - you are currently following it. Do NOT use the skill tool to load "using-harness" again — that would be redundant.**

${content}

${toolMapping}
</EXTREMELY_IMPORTANT>`;
  };

  return {
    // Inject skills path into live config so OpenCode discovers Harness skills
    // without requiring manual symlinks or config file edits.
    config: async (config) => {
      config.skills = config.skills || {};
      config.skills.paths = config.skills.paths || [];
      if (!config.skills.paths.includes(harnessSkillsDir)) {
        config.skills.paths.push(harnessSkillsDir);
      }
    },

    // Inject bootstrap into the first user message of each session.
    // Using a user message instead of a system message avoids:
    //   1. Token bloat from system messages repeated every turn
    //   2. Multiple system messages breaking Qwen and other models
    'experimental.chat.messages.transform': async (_input, output) => {
      const bootstrap = getBootstrapContent();
      if (!bootstrap || !output.messages.length) return;
      const firstUser = output.messages.find(m => m.info.role === 'user');
      if (!firstUser || !firstUser.parts.length) return;
      // Only inject once
      if (firstUser.parts.some(p => p.type === 'text' && p.text.includes('EXTREMELY_IMPORTANT'))) return;
      const ref = firstUser.parts[0];
      firstUser.parts.unshift({ ...ref, type: 'text', text: bootstrap });
    }
  };
};
