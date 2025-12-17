---
description: Squash all commits since base into single commit with Conventional Commits format
argument-hint: [base-ref] [tag]
project-agnostic: true
allowed-tools:
  - Bash
  - Read
  - Skill
---

# Squash Command

Squash all commits since base reference into a single commit with standardized Conventional Commits message.

## Context Awareness

**INVOKE** `git-rewrite-history` skill to gain context about safe history rewriting patterns.

**Arguments:**
- `$1` (optional): Base reference - branch name or commit hash (default: merge-base with main)
- `$2` (optional): Tag to delete and recreate on squashed commit

## Pre-Flight Checks

### 1. Working Tree Status
```bash
git status --porcelain
```

If output is NOT empty: **STOP** - "Working tree is dirty. Commit or stash changes first."

### 2. Current Branch
```bash
git branch --show-current
```

If branch is `main` or `master`: **STOP** - "Cannot squash on protected branch."

### 3. Resolve Base Reference

**If `$1` provided:**
- Check if it's a branch: `git show-ref --verify refs/heads/$1 2>/dev/null`
- If branch exists: resolve via `git merge-base $1 HEAD`
- Otherwise treat as commit hash and use directly

**If `$1` NOT provided:**
- Default: `git merge-base main HEAD`

### 4. Count Commits
```bash
git rev-list --count <base>..HEAD
```

If count is 0: **STOP** - "No commits to squash."

### 5. Tag Check (if `$2` provided)
```bash
git tag -l "$2"
```

If tag doesn't exist: **WARN** - "Tag '$2' doesn't exist. Will create new tag."

## Confirmation Gate

**STOP HERE** and show:

```
Squash Summary:
- Branch: [current branch]
- Base: [resolved base commit - short hash]
- Commits to squash: [count]
- Tag: [tag name or "none"]
- Commit list:
  [git log --oneline <base>..HEAD]

This will REWRITE HISTORY locally. Proceed? (yes/no)
```

**Wait for explicit "yes"**. Any other response = abort.

## Execution

### 1. Delete Tag (if provided and exists)
```bash
git tag -d $2
```

### 2. Soft Reset
```bash
git reset --soft <base>
```

### 3. Analyze Changes for Commit Message

**Get diff for analysis:**
```bash
git diff <base>..HEAD --stat
git diff <base>..HEAD --name-status
```

**Determine commit type from changes:**
- `feat`: New files/features added
- `fix`: Bug fixes (look for "fix" in original commits or test corrections)
- `refactor`: Code restructuring without behavior change
- `docs`: Documentation-only changes (*.md, comments)
- `chore`: Build, config, tooling changes
- `test`: Test-only changes

**Determine scope from changed paths:**
- Extract primary directory/component from changed files
- Use most common parent directory as scope
- Examples: `commands`, `skills`, `core`, `config`, `api`, `ui`

**Get original commit messages:**
```bash
git log --format="- %s" <base>..HEAD
```

### 4. Generate Conventional Commit Message

**Title format:** `<type>(<scope>): <description>`
- Type: Determined from change analysis
- Scope: Primary component/directory affected
- Description: Concise summary (imperative mood, lowercase, no period)

**Body format with sections (include only non-empty):**

```
## Added
- New feature/file descriptions

## Changed
- Modifications to existing functionality

## Fixed
- Bug fixes and corrections

## Removed
- Deleted files/features

Squashed commits:
- Original commit 1
- Original commit 2
...
```

### 5. Create Squashed Commit

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

## Added
- [list if any]

## Changed
- [list if any]

## Fixed
- [list if any]

## Removed
- [list if any]

Squashed commits:
[original commit list]
EOF
)"
```

### 6. Recreate Tag (if provided)
```bash
git tag $2
```

## Verification

Show final state:
```bash
git log --oneline <base>..HEAD
git show --stat HEAD
```

If tagged:
```bash
git tag -l --points-at HEAD
```

## Result Summary

```
Squash complete:
- [count] commits -> 1 commit ([short hash])
- Type: [commit type]
- Scope: [scope]
- Tag: [tag or "none"]
- LOCAL ONLY - not pushed
```
