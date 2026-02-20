# A-001 - Plugin Directory Restructure

## Human Section

### Goal
Restructure the agentic-config repository layout to conform to Claude Code plugin directory conventions. Create the foundational `.claude-plugin/plugin.json` manifest and move all commands, skills, and agents to plugin-standard locations.

### Constraints
- Must preserve all existing functionality during transition
- Must not break current symlink-based installations (yet)
- Plugin root structure must pass `claude plugin validate .`

---

## AI Section

### Scope

**Input:** Current structure with `core/commands/claude/`, `core/skills/`, `core/agents/`
**Output:** Plugin-compatible structure with `commands/`, `skills/`, `agents/` at plugin root

### Tasks

1. Create `.claude-plugin/plugin.json` manifest:
   ```json
   {
     "name": "agentic",
     "description": "Agentic workflow automation for AI-assisted development",
     "version": "1.0.0",
     "author": {
       "name": "Agentic Config"
     },
     "repository": "https://github.com/WaterplanAI/agentic-config",
     "license": "MIT",
     "keywords": ["workflow", "spec", "orchestration", "development"]
   }
   ```

2. Create plugin-root `commands/` directory:
   - Copy/move 35 command .md files from `core/commands/claude/`
   - Preserve command names (filename = command name)

3. Create plugin-root `skills/` directory:
   - Move 19 skill directories from `core/skills/`
   - Ensure each has proper `SKILL.md` with frontmatter

4. Create plugin-root `agents/` directory:
   - Move 8 agent .md files from `core/agents/`
   - Ensure proper frontmatter (name, description)

5. Validate with `claude plugin validate .`

6. Test with `claude --plugin-dir .`

### Research Context (from 001-claude-code-plugin-docs.md)
- Components (commands/, agents/, skills/, hooks/) must be at plugin root, NOT inside `.claude-plugin/`
- Only `plugin.json` goes inside `.claude-plugin/`
- `plugin.json` only requires `name` field; version, description, author, etc. are optional
- Custom paths in manifest supplement default directories (do not replace them)
- Commands in `commands/` are legacy; `skills/` preferred for new development
- If skill and command share same name, skill takes precedence

### Research Context (from 003-repo-structure-analysis.md)
- 35 commands in core/commands/claude/ (all .md files)
- 19 skills in core/skills/ (each with SKILL.md)
- 8 agents in core/agents/ (lifecycle agents + spec-command)
- Additional: 13 spec stage definitions in core/agents/spec/

### Acceptance Criteria
- `claude plugin validate .` passes
- `claude --plugin-dir .` loads all commands, skills, agents
- All command names visible via `/help`
- No broken references within plugin
- `core/` directory preserved for backward compatibility during transition

### Dependencies
None (foundation phase)

### Estimated Complexity
Medium -- primarily file reorganization with validation

---

## Plan

### Files

- `.claude-plugin/plugin.json` (NEW)
  - Plugin manifest with name, description, version, author, repository, license, keywords
- `agents` (MODIFY -- remove symlink, create real directory)
  - Remove symlink `agents -> core/agents`
  - Create real `agents/` directory with 7 .md files + `spec/` subdirectory
- `commands/` (NEW directory)
  - 35 .md files copied from `core/commands/claude/`
- `skills/` (NEW directory)
  - 19 skill directories copied from `core/skills/`
- `.gitignore` (MODIFY)
  - Add entries for new plugin-root directories that are copies of core/
- `core/` (UNCHANGED -- preserved entirely)
- `.claude/` (UNCHANGED -- preserved entirely)

### Tasks

#### Task 1 -- Create `.claude-plugin/plugin.json`

Tools: shell, editor

Steps:
1. Create the `.claude-plugin/` directory
2. Create `plugin.json` with full metadata

Commands:
```bash
mkdir -p .claude-plugin
```

File content for `.claude-plugin/plugin.json`:
````diff
--- /dev/null
+++ b/.claude-plugin/plugin.json
@@ -0,0 +1,13 @@
+{
+  "name": "agentic",
+  "description": "Agentic workflow automation for AI-assisted development",
+  "version": "1.0.0",
+  "author": {
+    "name": "Agentic Config"
+  },
+  "repository": "https://github.com/agentic-config/agentic-config",
+  "license": "MIT",
+  "keywords": ["workflow", "spec", "orchestration", "development"]
+}
````

Verification:
- `cat .claude-plugin/plugin.json | python3 -m json.tool` -- must parse without errors
- `[ -f .claude-plugin/plugin.json ] && echo "OK" || echo "FAIL"`

#### Task 2 -- Resolve `agents` symlink conflict and create plugin-root `agents/`

Tools: shell

The top-level `agents` is currently a symlink to `core/agents`. It must become a real directory for the plugin system. The approach: remove symlink, create real directory, copy all agent files and the `spec/` subdirectory.

Steps:
1. Remove the `agents` symlink at project root
2. Create `agents/` as a real directory
3. Copy 7 agent .md files from `core/agents/`
4. Copy `spec/` subdirectory with all 13 stage definition files

Commands:
```bash
# Remove symlink (NOT the target -- rm on symlink removes only the link)
rm agents

# Create real agents directory
mkdir -p agents/spec

# Copy 7 agent .md files
cp core/agents/agentic-customize.md agents/
cp core/agents/agentic-migrate.md agents/
cp core/agents/agentic-setup.md agents/
cp core/agents/agentic-status.md agents/
cp core/agents/agentic-update.md agents/
cp core/agents/agentic-validate.md agents/
cp core/agents/spec-command.md agents/

# Copy spec stage files (13 files + _template)
cp core/agents/spec/_template.md agents/spec/
cp core/agents/spec/AMEND.md agents/spec/
cp core/agents/spec/CREATE.md agents/spec/
cp core/agents/spec/DOCUMENT.md agents/spec/
cp core/agents/spec/FIX.md agents/spec/
cp core/agents/spec/IMPLEMENT.md agents/spec/
cp core/agents/spec/PLAN_REVIEW.md agents/spec/
cp core/agents/spec/PLAN.md agents/spec/
cp core/agents/spec/RESEARCH.md agents/spec/
cp core/agents/spec/REVIEW.md agents/spec/
cp core/agents/spec/TEST.md agents/spec/
cp core/agents/spec/VALIDATE_INLINE.md agents/spec/
cp core/agents/spec/VALIDATE.md agents/spec/
```

Verification:
- `[ -d agents ] && [ ! -L agents ] && echo "OK: real directory" || echo "FAIL: still symlink"`
- `ls agents/*.md | wc -l` -- must be 7
- `ls agents/spec/*.md | wc -l` -- must be 13
- `diff <(ls core/agents/*.md | xargs -I{} basename {}) <(ls agents/*.md | xargs -I{} basename {})` -- must be empty (identical file lists)

#### Task 3 -- Create plugin-root `commands/` directory

Tools: shell

Copy all 35 command .md files from `core/commands/claude/` to plugin-root `commands/`.

Commands:
```bash
mkdir -p commands
cp core/commands/claude/*.md commands/
```

Verification:
- `ls commands/*.md | wc -l` -- must be 35
- `diff <(ls core/commands/claude/ | sort) <(ls commands/ | sort)` -- must be empty (identical file lists)

#### Task 4 -- Create plugin-root `skills/` directory

Tools: shell

Copy all 19 skill directories from `core/skills/` to plugin-root `skills/`. Use `cp -R` to preserve directory structure and all supporting files within each skill.

Commands:
```bash
mkdir -p skills
cp -R core/skills/agent-orchestrator-manager skills/
cp -R core/skills/command-writer skills/
cp -R core/skills/cpc skills/
cp -R core/skills/dr skills/
cp -R core/skills/dry-run skills/
cp -R core/skills/gh-assets-branch-mgmt skills/
cp -R core/skills/git-find-fork skills/
cp -R core/skills/git-rewrite-history skills/
cp -R core/skills/gsuite skills/
cp -R core/skills/had skills/
cp -R core/skills/hook-writer skills/
cp -R core/skills/human-agentic-design skills/
cp -R core/skills/mux skills/
cp -R core/skills/mux-ospec skills/
cp -R core/skills/mux-subagent skills/
cp -R core/skills/playwright-cli skills/
cp -R core/skills/product-manager skills/
cp -R core/skills/single-file-uv-scripter skills/
cp -R core/skills/skill-writer skills/
```

Verification:
- `ls -d skills/*/ | wc -l` -- must be 19
- `diff <(ls -d core/skills/*/ | xargs -I{} basename {}) <(ls -d skills/*/ | xargs -I{} basename {})` -- must be empty
- `for d in skills/*/; do [ -f "$d/SKILL.md" ] || echo "MISSING: $d/SKILL.md"; done` -- must produce no output

#### Task 5 -- Update `.gitignore` for plugin-root directories

Tools: editor

The new plugin-root `commands/`, `skills/`, and `agents/` directories are copies of files already tracked under `core/`. To avoid tracking duplicate content and keep the repo clean during transition, add these to `.gitignore`. The `.claude-plugin/` directory MUST be tracked (it is the plugin manifest).

NOTE: The `agents` entry replaces the old symlink that was tracked. Since we removed the symlink and replaced it with a directory of copies, the directory should be gitignored to avoid duplicating tracked content. The canonical source remains `core/`.

````diff
--- a/.gitignore
+++ b/.gitignore
@@ -43,3 +43,10 @@

 # Invalid nested symlinks (artifacts from misconfigured setups)
 core/agents/agents
+
+# Plugin-root directories (copies of core/ for plugin compatibility)
+# Canonical source remains core/; these are generated during plugin build
+/commands/
+/skills/
+# agents/ was previously a symlink to core/agents, now a real directory copy
+/agents/
````

Verification:
- `git check-ignore commands/agentic.md` -- must output the path (confirmed ignored)
- `git check-ignore skills/mux/SKILL.md` -- must output the path (confirmed ignored)
- `git check-ignore agents/spec-command.md` -- must output the path (confirmed ignored)
- `git check-ignore .claude-plugin/plugin.json && echo "BAD" || echo "OK: not ignored"` -- must print "OK: not ignored"

#### Task 6 -- Validate plugin structure

Tools: shell

Run Claude Code plugin validation to confirm the directory structure is correct.

Commands:
```bash
claude plugin validate .
```

Expected output: Validation passes with no errors. All components discovered:
- 35 commands in `commands/`
- 19 skills in `skills/`
- 7 agents in `agents/`

If validation fails:
- Check `claude plugin validate . --debug` for detailed error info
- Common issues: invalid JSON in plugin.json, missing SKILL.md frontmatter, missing agent frontmatter
- Fix any issues and re-run validation

Verification:
- Exit code 0 from `claude plugin validate .`

#### Task 7 -- Test plugin loading

Tools: shell

Test that the plugin loads correctly with Claude Code.

Commands:
```bash
# Test plugin loading (non-interactive, just verify it loads)
claude --plugin-dir . -p "List your available slash commands" --output-format text 2>&1 | head -50
```

Verification:
- Output should include command names from the plugin (e.g., `/spec`, `/branch`, `/agentic`)
- No error messages about failed plugin loading
- If commands are not visible, check that `.claude-plugin/plugin.json` is valid and component directories exist at plugin root

#### Task 8 -- E2E verification checklist

Tools: shell

Run all acceptance criteria checks in sequence.

Commands:
```bash
echo "=== Check 1: plugin.json exists and is valid JSON ==="
python3 -m json.tool .claude-plugin/plugin.json > /dev/null && echo "PASS" || echo "FAIL"

echo "=== Check 2: commands/ has 35 files ==="
count=$(ls commands/*.md 2>/dev/null | wc -l | tr -d ' ')
[ "$count" -eq 35 ] && echo "PASS ($count)" || echo "FAIL ($count)"

echo "=== Check 3: skills/ has 19 directories ==="
count=$(ls -d skills/*/ 2>/dev/null | wc -l | tr -d ' ')
[ "$count" -eq 19 ] && echo "PASS ($count)" || echo "FAIL ($count)"

echo "=== Check 4: agents/ has 7 .md files ==="
count=$(ls agents/*.md 2>/dev/null | wc -l | tr -d ' ')
[ "$count" -eq 7 ] && echo "PASS ($count)" || echo "FAIL ($count)"

echo "=== Check 5: agents/spec/ has 13 files ==="
count=$(ls agents/spec/*.md 2>/dev/null | wc -l | tr -d ' ')
[ "$count" -eq 13 ] && echo "PASS ($count)" || echo "FAIL ($count)"

echo "=== Check 6: core/ preserved ==="
[ -d core/commands/claude ] && [ -d core/skills ] && [ -d core/agents ] && echo "PASS" || echo "FAIL"

echo "=== Check 7: .claude/ symlinks intact ==="
[ -L .claude/commands/spec.md ] && [ -L .claude/skills/mux ] && [ -L .claude/agents/spec-command.md ] && echo "PASS" || echo "FAIL"

echo "=== Check 8: agents/ is real directory (not symlink) ==="
[ -d agents ] && [ ! -L agents ] && echo "PASS" || echo "FAIL"

echo "=== Check 9: No broken references in agents/ ==="
diff <(ls core/agents/*.md | xargs -I{} basename {} | sort) <(ls agents/*.md | xargs -I{} basename {} | sort) && echo "PASS" || echo "FAIL"

echo "=== Check 10: All skills have SKILL.md ==="
missing=0; for d in skills/*/; do [ -f "$d/SKILL.md" ] || { echo "MISSING: $d"; missing=1; }; done
[ "$missing" -eq 0 ] && echo "PASS" || echo "FAIL"
```

Verification:
- ALL checks must print "PASS"
- Any "FAIL" must be investigated and fixed before proceeding to commit

#### Task 9 -- Commit changes

Tools: git

Commit only the tracked files that were modified. The plugin-root `commands/`, `skills/`, and `agents/` directories are gitignored (Task 5), so they will NOT be committed. Only `.claude-plugin/plugin.json` and `.gitignore` are committed.

The removal of the `agents` symlink is a tracked change (symlink was tracked in git).

Commands:
```bash
# Stage the new plugin manifest
git add .claude-plugin/plugin.json

# Stage .gitignore changes
git add .gitignore

# Stage removal of agents symlink (git tracks symlink removal as a deletion)
git add agents

# Verify staged changes
git status

# Commit
git commit -m "$(cat <<'EOF'
feat(plugin): create plugin directory structure for Claude Code plugin system

Added:
- .claude-plugin/plugin.json manifest with full metadata
- .gitignore entries for plugin-root component directories

Changed:
- Removed agents -> core/agents symlink (replaced by plugin-root agents/ directory)

Note: Plugin-root commands/, skills/, agents/ directories are gitignored copies
of core/ for plugin compatibility. Canonical source remains core/.
EOF
)"
```

Verification:
- `git log --oneline -1` -- must show the commit message
- `git status` -- must show clean working tree (ignoring untracked/gitignored files)
- `git diff HEAD~1 --name-only` -- must show: `.claude-plugin/plugin.json`, `.gitignore`, `agents` (symlink removal)

### Validate

Validation of compliance with Human Section requirements:

- **L6: "Restructure the agentic-config repository layout to conform to Claude Code plugin directory conventions"** -- Task 1 creates plugin.json, Tasks 2-4 create plugin-root directories with components. Validated via Task 6 (`claude plugin validate .`).
- **L7: "Create the foundational `.claude-plugin/plugin.json` manifest"** -- Task 1 creates plugin.json with all requested fields (name, description, version, author, repository, license, keywords).
- **L9: "Must preserve all existing functionality during transition"** -- `core/` is NEVER modified (Task 2-4 use `cp`, not `mv`). `.claude/` symlinks remain untouched. Verified in Task 8 checks 6-7.
- **L10: "Must not break current symlink-based installations (yet)"** -- `.claude/commands/`, `.claude/skills/`, `.claude/agents/` symlinks all point to `core/` and remain intact. The only symlink removed is the top-level `agents -> core/agents` which is replaced by a real directory with identical content.
- **L11: "Plugin root structure must pass `claude plugin validate .`"** -- Task 6 runs validation. Task 7 tests loading.
- **Acceptance: All command names visible via /help** -- Task 7 verifies commands appear when loading plugin.
- **Acceptance: No broken references within plugin** -- Task 8 checks 9-10 verify file parity.
- **Acceptance: `core/` preserved for backward compatibility** -- Task 8 check 6 confirms core/ intact.
