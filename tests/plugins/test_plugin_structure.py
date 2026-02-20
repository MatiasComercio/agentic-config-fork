#!/usr/bin/env python3
"""Plugin structure validation tests.

Validates that each plugin has correct structure, file counts,
and no forbidden external references.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

# Resolve plugins root relative to this test file
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"

EXPECTED_PLUGINS = {
    "agentic",
    "agentic-spec",
    "agentic-mux",
    "agentic-git",
    "agentic-review",
    "agentic-tools",
}

EXPECTED_COMMANDS = {
    "agentic": {"agentic.md", "agentic-setup.md", "agentic-status.md",
                "agentic-update.md", "agentic-migrate.md", "agentic-export.md",
                "agentic-import.md", "agentic-share.md", "branch.md", "spawn.md"},
    "agentic-spec": {"spec.md", "o_spec.md", "po_spec.md"},
    "agentic-mux": {"orc.md", "mux-roadmap.md"},
    "agentic-git": {"pull_request.md", "squash.md", "rebase.md",
                    "squash_commit.md", "squash_and_rebase.md", "release.md"},
    "agentic-review": {"e2e_review.md", "gh_pr_review.md",
                       "full-life-cycle-pr.md", "e2e-template.md", "test_e2e.md"},
    "agentic-tools": {"browser.md", "video_query.md", "fork-terminal.md",
                      "milestone.md", "worktree.md", "adr.md", "ac-issue.md",
                      "prepare_app.md", "setup-voice-mode.md"},
}

EXPECTED_SKILLS = {
    "agentic": {"cpc", "dr", "had", "human-agentic-design",
                "command-writer", "skill-writer", "hook-writer"},
    "agentic-spec": set(),
    "agentic-mux": {"mux", "mux-ospec", "mux-subagent",
                    "agent-orchestrator-manager", "product-manager"},
    "agentic-git": {"git-find-fork", "git-rewrite-history",
                    "gh-assets-branch-mgmt"},
    "agentic-review": {"dry-run", "single-file-uv-scripter"},
    "agentic-tools": {"gsuite", "playwright-cli"},
}

# Patterns that indicate internal library dependencies (strictly forbidden)
FORBIDDEN_PATTERNS = [
    r'AGENTIC_GLOBAL',
    r'_AGENTIC_ROOT',
    r'~/.agents/agentic-config',
    r'core/lib/',
    r'core/tools/',
    r'core/prompts/',
    r'core/hooks/',
    r'core/scripts/',
]

# Allowed exceptions
ALLOWED_EXCEPTIONS = [
    r'~/.agents/customization/',  # User-data path, exempt (SC9)
]

# Files exempt from certain checks (setup scripts that manage target projects)
SETUP_SCRIPT_EXEMPTIONS = {
    "update-config.sh",  # Manages monolithic installation targets
}


class TestPluginExists(unittest.TestCase):
    def test_all_plugins_exist(self) -> None:
        actual = {d.name for d in PLUGINS_DIR.iterdir() if d.is_dir()}
        self.assertEqual(actual, EXPECTED_PLUGINS)


class TestPluginManifest(unittest.TestCase):
    def test_each_plugin_has_valid_plugin_json(self) -> None:
        names: set[str] = set()
        for plugin in EXPECTED_PLUGINS:
            pj = PLUGINS_DIR / plugin / ".claude-plugin" / "plugin.json"
            self.assertTrue(pj.exists(), f"Missing plugin.json for {plugin}")
            data = json.loads(pj.read_text())
            self.assertIn("name", data)
            self.assertIn("version", data)
            self.assertIn("description", data)
            self.assertNotIn(data["name"], names, f"Duplicate name: {data['name']}")
            names.add(data["name"])


class TestCommandDistribution(unittest.TestCase):
    def test_commands_per_plugin(self) -> None:
        for plugin, expected in EXPECTED_COMMANDS.items():
            cmd_dir = PLUGINS_DIR / plugin / "commands"
            if expected:
                self.assertTrue(cmd_dir.exists(), f"Missing commands/ for {plugin}")
                actual = {f.name for f in cmd_dir.iterdir() if f.suffix == ".md"}
                self.assertEqual(actual, expected, f"Command mismatch for {plugin}")


class TestSkillDistribution(unittest.TestCase):
    def test_skills_per_plugin(self) -> None:
        for plugin, expected in EXPECTED_SKILLS.items():
            skills_dir = PLUGINS_DIR / plugin / "skills"
            if expected:
                self.assertTrue(skills_dir.exists(), f"Missing skills/ for {plugin}")
                actual = {d.name for d in skills_dir.iterdir() if d.is_dir()}
                self.assertEqual(actual, expected, f"Skill mismatch for {plugin}")
            # If no skills expected, skills/ dir may not exist (OK)

    def test_each_skill_has_skill_md(self) -> None:
        for plugin in EXPECTED_PLUGINS:
            skills_dir = PLUGINS_DIR / plugin / "skills"
            if not skills_dir.exists():
                continue
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    self.assertTrue(
                        (skill_dir / "SKILL.md").exists(),
                        f"Missing SKILL.md in {skill_dir}",
                    )


class TestNoForbiddenLibraryDeps(unittest.TestCase):
    """Verify no forbidden internal library references remain."""

    def test_no_forbidden_patterns_in_plugins(self) -> None:
        violations: list[str] = []
        for root, _dirs, files in os.walk(PLUGINS_DIR):
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix not in (".md", ".sh", ".py", ".json"):
                    continue
                # Skip setup script exemptions
                if fpath.name in SETUP_SCRIPT_EXEMPTIONS:
                    continue
                content = fpath.read_text(errors="replace")
                for pattern in FORBIDDEN_PATTERNS:
                    matches = list(re.finditer(pattern, content))
                    if matches:
                        for match in matches:
                            context_start = max(0, match.start() - 50)
                            context = content[context_start:match.start() + 100]
                            # Check allowed exceptions
                            is_allowed = any(
                                re.search(exc, context) for exc in ALLOWED_EXCEPTIONS
                            )
                            # Also allow comment-only lines for agentic-root.sh references
                            line_start = content.rfind('\n', 0, match.start()) + 1
                            line_end = content.find('\n', match.end())
                            line = content[line_start:line_end if line_end != -1 else None].strip()
                            is_comment = line.startswith('#')
                            if not is_allowed and not is_comment:
                                violations.append(
                                    f"{fpath.relative_to(REPO_ROOT)}: "
                                    f"forbidden pattern '{pattern}'"
                                )
                                break  # One violation per pattern per file
        self.assertEqual(violations, [], "\n".join(violations))


class TestNoParentDirectoryTraversal(unittest.TestCase):
    def test_no_parent_directory_traversal_in_plugin_json(self) -> None:
        """Plugin manifests and hooks.json must not reference ../."""
        violations: list[str] = []
        for plugin in EXPECTED_PLUGINS:
            plugin_dir = PLUGINS_DIR / plugin
            for json_file in [
                plugin_dir / ".claude-plugin" / "plugin.json",
                plugin_dir / "hooks" / "hooks.json",
            ]:
                if not json_file.exists():
                    continue
                content = json_file.read_text(errors="replace")
                if "../" in content:
                    violations.append(str(json_file.relative_to(REPO_ROOT)))
        self.assertEqual(violations, [], f"Parent traversal in plugin manifests: {violations}")

    def test_no_escape_traversal_in_scripts(self) -> None:
        """Shell scripts must not use ../ to escape plugin root (ln -sf ../../ within cd subshells is OK)."""
        # This is a documentation-level check - scripts may use relative paths
        # for linking within target projects (e.g., setup-config.sh, update-config.sh)
        # but should not have source/import paths with ../
        violations: list[str] = []
        exempt_patterns = [
            r'ln -sf.*\.\.',      # Symlink operations (target project setup)
            r'cd.*&&.*\.\./',     # cd to subdirectory then reference parent
            r'\.\.\/',             # Any ../ in exempt scripts
        ]
        exempt_files = SETUP_SCRIPT_EXEMPTIONS | {
            "update-config.sh", "setup-config.sh", "migrate-existing.sh",
        }
        for root, _dirs, files in os.walk(PLUGINS_DIR):
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix not in (".sh",) or fpath.name in exempt_files:
                    continue
                content = fpath.read_text(errors="replace")
                for line_num, line in enumerate(content.splitlines(), 1):
                    # Only flag source or import statements with ../
                    stripped = line.strip()
                    if re.search(r'source\s+.*\.\./', line) or re.search(r'^\.\s+.*\.\./', line):
                        if not stripped.startswith('#'):
                            violations.append(
                                f"{fpath.relative_to(REPO_ROOT)}:{line_num}: "
                                f"parent traversal in source: {stripped[:80]}"
                            )
        self.assertEqual(violations, [], "\n".join(violations))


class TestSpecResolver(unittest.TestCase):
    def test_spec_resolver_exists_in_agentic_spec(self) -> None:
        sr = PLUGINS_DIR / "agentic-spec" / "scripts" / "spec-resolver.sh"
        self.assertTrue(sr.exists())

    def test_spec_resolver_uses_plugin_root(self) -> None:
        sr = PLUGINS_DIR / "agentic-spec" / "scripts" / "spec-resolver.sh"
        content = sr.read_text()
        self.assertIn("CLAUDE_PLUGIN_ROOT", content)
        self.assertNotIn("AGENTIC_GLOBAL", content)
        self.assertNotIn("_AGENTIC_ROOT", content)

    def test_config_loader_exists_in_agentic_spec(self) -> None:
        cl = PLUGINS_DIR / "agentic-spec" / "scripts" / "lib" / "config-loader.sh"
        self.assertTrue(cl.exists())

    def test_spec_stage_agents_use_plugin_root(self) -> None:
        spec_agents_dir = PLUGINS_DIR / "agentic-spec" / "agents" / "spec"
        violations = []
        for agent_file in spec_agents_dir.glob("*.md"):
            content = agent_file.read_text()
            if "AGENTIC_GLOBAL" in content or "core/lib/spec-resolver" in content:
                violations.append(str(agent_file.name))
        self.assertEqual(violations, [], f"Agents still reference AGENTIC_GLOBAL: {violations}")


class TestHooksDistribution(unittest.TestCase):
    def test_agentic_has_global_hooks(self) -> None:
        hj = PLUGINS_DIR / "agentic" / "hooks" / "hooks.json"
        self.assertTrue(hj.exists())
        data = json.loads(hj.read_text())
        hooks = data["hooks"]["PreToolUse"]
        self.assertEqual(len(hooks), 2, "agentic should have 2 global hooks")

    def test_agentic_tools_has_gsuite_hook(self) -> None:
        hj = PLUGINS_DIR / "agentic-tools" / "hooks" / "hooks.json"
        self.assertTrue(hj.exists())
        data = json.loads(hj.read_text())
        hooks = data["hooks"]["PreToolUse"]
        self.assertEqual(len(hooks), 1, "agentic-tools should have 1 hook")

    def test_hooks_use_plugin_root(self) -> None:
        for plugin in ["agentic", "agentic-tools"]:
            hj = PLUGINS_DIR / plugin / "hooks" / "hooks.json"
            if hj.exists():
                content = hj.read_text()
                self.assertIn("CLAUDE_PLUGIN_ROOT", content)
                self.assertNotIn("AGENTIC_GLOBAL", content)


class TestMuxPythonTools(unittest.TestCase):
    def test_mux_tools_exist(self) -> None:
        tools_dir = PLUGINS_DIR / "agentic-mux" / "scripts" / "tools"
        expected_tools = {
            "spawn.py", "spec.py", "researcher.py", "ospec.py",
            "oresearch.py", "coordinator.py", "campaign.py",
        }
        for tool in expected_tools:
            self.assertTrue(
                (tools_dir / tool).exists(),
                f"Missing tool: {tool}",
            )

    def test_mux_prompts_exist(self) -> None:
        prompts_dir = PLUGINS_DIR / "agentic-mux" / "scripts" / "prompts"
        count = sum(1 for _ in prompts_dir.rglob("*.md"))
        self.assertEqual(count, 10, f"Expected 10 prompt files, found {count}")

    def test_mux_dynamic_hooks_exist(self) -> None:
        hooks_dir = PLUGINS_DIR / "agentic-mux" / "scripts" / "hooks"
        expected = {
            "mux-bash-validator.py",
            "mux-forbidden-tools.py",
            "mux-task-validator.py",
        }
        actual = {f.name for f in hooks_dir.glob("*.py")}
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
