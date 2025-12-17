# Project-Specific Guidelines

Project overrides for agentic-config repository.

## Content Rules

- DO NOT use emojis in markdown files
- ALWAYS ensure every git-tracked asset is project-agnostic and anonymous
- All documentation and code must be anonymized (no personal names, emails, or identifiable information)

## Symlinks

CRITICAL - All project symlinks MUST use relative paths:
- Commands: Use `../../core/commands/claude/<name>` from `.claude/commands/`
- Skills: Use `../../core/skills/<name>` from `.claude/skills/`
- Agents: Use `../../core/agents/<name>` from `.claude/agents/`
- NEVER use absolute paths in symlinks
- Reference: .claude/commands/init.md for canonical implementation

## Git Commit Standards

This project uses Conventional Commits (https://conventionalcommits.org) with extended formatting:

- Format: `<type>(<scope>): <description>`
- Types: feat, fix, docs, chore, refactor, test, style, perf, build, ci
- Commit body uses structured sections: Added, Changed, Fixed, Removed
- Squashed commits include original commit list in body

## CHANGELOG

- Add new entries to `[Unreleased]` section
- DO NOT modify already released/tagged versions unless explicitly requested
