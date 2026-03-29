# Git Convention — Sata

> Team-grade Git workflow for the **Sata** workspace — aligned with the **file-organization** repo’s Git conventions (`GIT_CONVENTION.md`), usable from day one as a solo developer.
>
> **Philosophy:** Pay a small cost now, save massive refactoring later. Every rule here works for 1 person and 50 people alike.

---

## Table of Contents

- [Repository management (GitHub)](#repository-management-github)
- [Branch Model](#branch-model)
- [Branch Naming](#branch-naming)
- [Commit Convention](#commit-convention)
- [Pull Request Workflow](#pull-request-workflow)
- [PR Template](#pr-template)
- [Code Review Guidelines](#code-review-guidelines)
- [Merge Strategy](#merge-strategy)
- [Versioning & Tagging](#versioning--tagging)
- [Release Process](#release-process)
- [Hotfix Process](#hotfix-process)
- [Changelog](#changelog)
- [Branch Protection Rules](#branch-protection-rules)
- [Git Hooks](#git-hooks)
- [CI/CD Pipeline](#cicd-pipeline)
- [CODEOWNERS](#codeowners)
- [Project-Specific Profiles](#project-specific-profiles)
- [Repo Setup Checklist](#repo-setup-checklist)
- [Quick Reference](#quick-reference)

---

## Repository management (GitHub)

This section is the **repo manager** view: where the repository lives, who decides merges, and what to configure once.

### Roles

| Role | Responsibility |
|------|----------------|
| **Release manager** | Approves merges to `main`, cuts tags, owns `release/*` and `hotfix/*`. On a solo repo, that is you. |
| **Contributors** | Branch from `develop`, open PRs, keep branches short-lived. |

### Where to manage the repository

| Task | Location on GitHub |
|------|---------------------|
| Branch protection, required reviews, status checks | **Settings → Rules → Rulesets** (or classic branch protection) |
| Default branch (`develop` recommended after bootstrap) | **Settings → General → Default branch** |
| Secrets for CI | **Settings → Secrets and variables → Actions** |
| Collaborators | **Settings → Collaborators** (or org teams) |
| Releases and tags | **Releases** (often driven by `.github/workflows/release.yml` on tag push) |

### Local and GUI tools

GitHub is the source of truth. You may use **Git CLI**, **GitHub Desktop**, **GitKraken**, or your editor’s Git UI — all must follow the same branch and commit rules in this document. Hooks in `.githooks/` apply regardless of client when `core.hooksPath` is set.

### Sata workspace context

Sata is a **Cursor / AI tooling workspace** (BMad skills, agent configuration, shared rules). It is not an app binary repo; CI jobs should run whatever validation fits the stack (lint markdown, validate skill manifests, etc.) when you add workflows.

---

## Branch Model

Use **Git Flow** as the standard model for all projects.

```
main ─────────────────●────────────────●──────────── (production, tagged)
                     ╱                ╱
release/1.0.0 ──────●               ╱
                    ╱               ╱
develop ───●───●───●───●───●───●───●──────────────── (integration)
          ╱   ╱       ╱   ╱       ╱
feat/a ●  ╱       ╱   ╱       ╱
            ╱       ╱   ╱       ╱
feat/b  ●       ╱   ╱       ╱
                  ╱   ╱       ╱
fix/bug-x        ●   ╱       ╱
                    ╱       ╱
hotfix/1.0.1 ─────●───────● (from main, merges back to main + develop)
```

### Branch Purposes

| Branch         | Lifetime    | Created From | Merges Into          | Who Can Merge       |
|----------------|-------------|--------------|----------------------|---------------------|
| `main`         | Permanent   | —            | —                    | Release manager     |
| `develop`      | Permanent   | `main`       | `release/*`          | Any via approved PR |
| `feat/*`    | Temporary   | `develop`    | `develop`            | Author via PR       |
| `fix/*`        | Temporary   | `develop`    | `develop`            | Author via PR       |
| `refactor/*`   | Temporary   | `develop`    | `develop`            | Author via PR       |
| `release/*`    | Temporary   | `develop`    | `main` + `develop`   | Release manager     |
| `hotfix/*`     | Temporary   | `main`       | `main` + `develop`   | Release manager     |

> **Solo note:** You are the release manager. The process is the same — just faster.

### Rules

- `main` and `develop` are **permanent** — never delete them.
- All other branches are **temporary** — delete after merge.
- No one pushes directly to `main` or `develop` — always via PR.
- Every temporary branch lives for **max 5 business days**. If longer, break it up.

---

## Branch Naming

### Format

```
<type>/<ticket-id>-<short-description>
```

When there is no ticket system, omit the ticket ID:

```
<type>/<short-description>
```

### Types

| Prefix        | Purpose                                       | Example                            |
|---------------|-----------------------------------------------|------------------------------------|
| `feat/`    | New user-facing functionality                 | `feat/42-sse-streaming`         |
| `fix/`        | Bug fix                                       | `fix/87-jwt-refresh-race`          |
| `refactor/`   | Code restructuring (no behavior change)       | `refactor/extract-auth-module`     |
| `chore/`      | Maintenance, deps, config                     | `chore/update-ktor-2.4`           |
| `docs/`       | Documentation only                            | `docs/api-rate-limits`             |
| `ci/`         | CI/CD pipeline changes                        | `ci/testflight-deploy`             |
| `test/`       | Test additions or fixes                       | `test/auth-unit-tests`             |
| `perf/`       | Performance improvements                      | `perf/image-cache-optimization`    |
| `release/`    | Release preparation                           | `release/1.2.0`                    |
| `hotfix/`     | Critical production fix                       | `hotfix/1.2.1`                     |
| `experiment/` | Spike / prototype (may be discarded)          | `experiment/compose-migration`     |

### Rules

- Lowercase only, hyphens for spaces.
- Max 50 characters total.
- Use present tense: `add-auth` not `added-auth`.
- Include ticket/issue ID when available.

---

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/) v1.0.0 strictly.

### Format

```
<type>(<scope>): <subject>
                                    ← blank line
[optional body]
                                    ← blank line
[optional footer(s)]
```

### Types

| Type       | Meaning                                  | SemVer Impact | Example                               |
|------------|------------------------------------------|---------------|---------------------------------------|
| `feat`     | New feature for the user                 | MINOR         | `feat(chat): add typing indicators`   |
| `fix`      | Bug fix for the user                     | PATCH         | `fix(auth): handle expired refresh`   |
| `docs`     | Documentation only                       | —             | `docs: update setup guide`            |
| `style`    | Formatting, whitespace (no logic change) | —             | `style: fix indentation in module`    |
| `refactor` | Code change, no fix or feature           | —             | `refactor(net): extract SSE client`   |
| `perf`     | Performance improvement                  | PATCH         | `perf(image): add disk cache layer`   |
| `test`     | Adding or correcting tests               | —             | `test(auth): add token refresh tests` |
| `chore`    | Build process, deps, tooling             | —             | `chore(deps): bump Ktor to 2.3.7`    |
| `ci`       | CI/CD configuration                      | —             | `ci: add GitHub Actions lint job`     |
| `revert`   | Reverts a previous commit                | varies        | `revert: feat(chat): add typing...`  |

### Subject Rules

1. **Imperative mood**: "add" not "added" or "adds".
2. **Lowercase** first letter.
3. **No period** at the end.
4. **Max 72 characters** (type + scope + subject combined).
5. **Complete the sentence**: "This commit will ___".

### Scope

Scope = the module, layer, or area affected. Define scopes per project and keep them consistent.

Common scopes:

```
auth, chat, networking, database, ui, shared, ios, android,
api, analytics, ci, deps, config, security
```

### Body

- Wrap at 72 characters per line.
- Explain **what** and **why**, not how (the code shows how).
- Use bullet points for multiple changes.

```
feat(auth): add biometric login support

Implement FaceID and TouchID authentication with fallback to
PIN entry. Reduces friction for returning users and satisfies
client security requirements (SOW §4.2).

- Add BiometricManager for cross-platform abstraction
- Update Keychain wrapper for biometric-protected entries
- Add fallback PIN entry screen with lockout policy
```

### Footer

```
Closes #42
Refs #38, #41
BREAKING CHANGE: auth token format changed to opaque tokens
Co-authored-by: Tri Nguyen <tri@example.com>
Reviewed-by: Son Tran <son@example.com>
```

### Breaking Changes

Use `!` after type AND add `BREAKING CHANGE:` footer (both):

```
feat(api)!: change auth endpoint response format

BREAKING CHANGE: POST /auth/login now returns
{ accessToken, refreshToken } instead of { token }.
All clients must update their token parsing logic.

Migration guide: docs/migration/v2-auth.md
```

---

## Pull Request Workflow

**Every change goes through a PR — no exceptions, even solo.**

### Lifecycle

```
1. Create branch from develop (or main for hotfix)
2. Make commits following convention
3. Push branch, open PR using template
4. CI runs automatically
5. Review (self-review if solo, peer review if team)
6. Address feedback, update branch
7. Squash commits on branch into one clean commit
8. Merge into target (merge commit --no-ff)
9. Delete branch
```

### PR Title

Must follow commit convention (this becomes the squashed commit on branch):

```
feat(chat): implement real-time SSE streaming (#42)
```

### PR Size Guidelines

| Size     | Lines Changed | Review Time | Recommendation                    |
|----------|---------------|-------------|-----------------------------------|
| XS       | 1–50          | < 15 min    | ✅ Ideal                          |
| S        | 51–200        | 15–30 min   | ✅ Good                           |
| M        | 201–500       | 30–60 min   | ⚠️ Consider splitting             |
| L        | 501–1000      | 1–2 hrs     | ❌ Split into smaller PRs          |
| XL       | 1000+         | > 2 hrs     | ❌ Must split (except migrations)  |

### Stacked PRs (for large features)

When a feature is too big for one PR, use stacked branches:

```
develop
 └── feat/42-auth-base        ← PR #1: models, interfaces
      └── feat/42-auth-ui     ← PR #2: UI layer (depends on #1)
           └── feat/42-auth-tests  ← PR #3: tests (depends on #2)
```

Merge in order: #1 → #2 → #3.

---

## PR Template

Save as `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## Summary

<!-- One-liner: what does this PR do? -->

## Motivation

<!-- Why is this change needed? Link to issue/ticket. -->

Closes #

## Changes

<!-- What did you change and why this approach? -->

-
-
-

## Type

- [ ] `feat` — New feature
- [ ] `fix` — Bug fix
- [ ] `refactor` — Restructuring (no behavior change)
- [ ] `perf` — Performance improvement
- [ ] `chore` — Maintenance / deps / config
- [ ] `docs` — Documentation
- [ ] `ci` — CI/CD changes
- [ ] `test` — Test additions / fixes
- [ ] `breaking` — Breaking change (describe in Migration section)

## Testing

- [ ] Unit tests added / updated
- [ ] Integration tests pass
- [ ] Manual testing on device (specify: ___)
- [ ] Edge cases considered and documented

## Screenshots / Recordings

<!-- Required for UI changes. Delete section if not applicable. -->

| Before | After |
|--------|-------|
|        |       |

## Migration Guide

<!-- Required for breaking changes. Delete section if not applicable. -->

## Checklist

- [ ] PR title follows commit convention
- [ ] Branch is rebased on latest target
- [ ] No unrelated changes included
- [ ] Self-reviewed the diff
- [ ] Documentation updated (if applicable)
- [ ] No TODOs left without linked issue

## Notes for Reviewers

<!-- Anything specific to focus on? Areas of uncertainty? -->
```

---

## Code Review Guidelines

### For Reviewers

| Priority  | Focus Area                                        |
|-----------|---------------------------------------------------|
| 🔴 Block  | Security issues, data loss risk, broken logic     |
| 🟡 Warn   | Performance concerns, missing tests, tech debt    |
| 🟢 Nit    | Style, naming, minor improvements                 |

### Review Etiquette

- **Comment on the code, not the person**: "This function could be simplified" not "You wrote this wrong".
- **Explain why**, not just what: "Consider extracting this — it'll make testing easier".
- **Use prefixes** in comments:

```
[blocking] This will cause a race condition in production.
[suggestion] Consider using a sealed class here for exhaustive matching.
[nit] Naming: fetchUser → getUser for consistency with codebase.
[question] What happens if the token is null here?
[praise] Nice abstraction — this will scale well.
```

### For Authors

- Self-review your diff before requesting review.
- Keep PR description complete — reviewers shouldn't need to ask "what does this do?".
- Respond to every comment (even if just "Done" or "Won't fix because...").
- Don't take feedback personally — it's about the code, not you.

> **Solo note:** Do a self-review on every PR. Read the diff as if someone else wrote it. You'll catch bugs you missed while coding.

---

## Merge Strategy

| Merge Target             | Strategy           | Rationale                              |
|--------------------------|--------------------|----------------------------------------|
| feat/fix → `develop`  | **Squash on branch + merge commit** | Clean commit + visible branch link |
| release → `main`         | **Merge commit**   | Preserve release branch context        |
| release → `develop`      | **Merge commit**   | Back-merge release stabilization       |
| hotfix → `main`          | **Merge commit**   | Traceability for production fix        |
| hotfix → `develop`       | **Cherry-pick**    | Avoid pulling unrelated main commits   |

### Squash on Branch Before Merge

Before merging, squash all commits on the feature branch into one:

```bash
# On feature branch, squash all commits since diverging from develop
git rebase -i develop
# Mark all commits except the first as "squash"
# Write final commit message following convention
```

Then on GitHub, use **"Create a merge commit"** (not "Squash and merge").

This gives you:
- One clean commit per feature (like squash merge)
- Visible branch connection on the graph (like merge commit)

### Squash Commit Format

The squash commit message = PR title + summary of changes:

```
feat(chat): implement real-time SSE streaming (#42)

- Add SSE client with automatic reconnection
- Implement live markdown rendering pipeline
- Add typing indicators with debounce
- Handle connection state management and retry logic

Co-authored-by: Tri Nguyen <tri@example.com>
```

### Rebase Rules

- **Rebase feature branches** onto `develop` before merging (keep linear history).
- **Never rebase** `main`, `develop`, `release/*`, or `hotfix/*`.
- **Never force-push** to shared branches.

---

## Versioning & Tagging

Follow [Semantic Versioning](https://semver.org/) 2.0.0.

### Format

```
v<MAJOR>.<MINOR>.<PATCH>[-<pre-release>][+<build>]
```

### When to Bump

| Change Type                        | Example                           | Version Bump |
|------------------------------------|-----------------------------------|--------------|
| Breaking API / behavior change     | Remove endpoint, change response  | **MAJOR**    |
| New feature, backward compatible   | Add new screen, new API endpoint  | **MINOR**    |
| Bug fix, backward compatible       | Fix crash, correct calculation    | **PATCH**    |
| Pre-release                        | Testing before stable release     | `-beta.1`    |

### Tag Commands

```bash
# Create annotated tag (always annotated, never lightweight)
git tag -a v1.2.0 -m "v1.2.0 — Real-time chat + performance improvements"

# Pre-release tags
git tag -a v2.0.0-alpha.1 -m "v2.0.0-alpha.1 — KMP migration alpha"
git tag -a v2.0.0-beta.1 -m "v2.0.0-beta.1 — KMP migration beta"
git tag -a v2.0.0-rc.1 -m "v2.0.0-rc.1 — KMP migration release candidate"

# Push
git push origin v1.2.0
git push origin --tags
```

### Tag Message Convention

```
v<VERSION> — <One-line summary>

Highlights:
- Key change 1
- Key change 2
- Key change 3

Full changelog: CHANGELOG.md
```

---

## Release Process

### Step-by-Step

```bash
# 1. Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/1.2.0

# 2. Bump version numbers in project files
#    (Info.plist, build.gradle, package.json, etc.)
git commit -m "chore(release): bump version to 1.2.0"

# 3. Stabilize — only bug fixes allowed on this branch
git commit -m "fix(release): correct dark mode toggle state"
git commit -m "fix(release): update outdated copy in onboarding"

# 4. Generate / update CHANGELOG.md
git commit -m "docs(release): update changelog for 1.2.0"

# 5. Merge into main (merge commit, no squash)
git checkout main
git pull origin main
git merge --no-ff release/1.2.0
git tag -a v1.2.0 -m "v1.2.0 — Chat feature + performance improvements"
git push origin main --tags

# 6. Back-merge into develop (merge commit, no squash)
git checkout develop
git merge --no-ff release/1.2.0
git push origin develop

# 7. Delete release branch
git branch -d release/1.2.0
git push origin --delete release/1.2.0
```

### Release Checklist

- [ ] All features for this release merged to `develop`.
- [ ] Release branch created and version bumped.
- [ ] Only bug fixes committed to release branch.
- [ ] QA / testing passed.
- [ ] CHANGELOG updated.
- [ ] Merged to `main` with annotated tag.
- [ ] Back-merged to `develop`.
- [ ] Release branch deleted.
- [ ] CI/CD deployed successfully.
- [ ] Stakeholders / users notified.

---

## Hotfix Process

For critical bugs in production that cannot wait for the next release.

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/1.2.1

# 2. Fix the issue (minimal, surgical changes only)
git commit -m "fix(auth): patch critical token validation bypass"

# 3. Bump patch version
git commit -m "chore(release): bump version to 1.2.1"

# 4. Update changelog
git commit -m "docs(release): update changelog for 1.2.1"

# 5. Merge into main and tag
git checkout main
git merge --no-ff hotfix/1.2.1
git tag -a v1.2.1 -m "v1.2.1 — Critical auth security fix"
git push origin main --tags

# 6. Cherry-pick into develop
git checkout develop
git cherry-pick -x <merge-commit-hash>
# Or if conflicts: merge the hotfix branch instead
# git merge --no-ff hotfix/1.2.1
git push origin develop

# 7. If a release branch exists, also cherry-pick there
git checkout release/1.3.0  # if exists
git cherry-pick -x <commit-hash>

# 8. Cleanup
git branch -d hotfix/1.2.1
git push origin --delete hotfix/1.2.1
```

### Hotfix Rules

- Hotfix branches contain **only the fix** — no features, no refactoring.
- Always bump PATCH version.
- Always update changelog.
- Must be merged to both `main` AND `develop` (and active `release/*` if any).

---

## Changelog

Maintain `CHANGELOG.md` in the repo root. Follow [Keep a Changelog](https://keepachangelog.com/) format.

### Format

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- SSE streaming client with auto-reconnect (#42)

### Fixed
- JWT refresh token race condition (#87)

## [1.1.0] - 2026-03-10

### Added
- Real-time chat with typing indicators (#35)
- Push notification support via FCM (#38)

### Changed
- Migrate networking layer to Ktor 2.3.7 (#40)

### Fixed
- Memory leak in image cache on iOS (#36)
- Dark mode toggle not persisting (#39)

## [1.0.0] - 2026-02-01

### Added
- Initial release with authentication and core features.

[Unreleased]: https://github.com/OWNER/sata/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/OWNER/sata/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/OWNER/sata/releases/tag/v1.0.0
```

### Categories

| Category      | What Goes Here                                    |
|---------------|---------------------------------------------------|
| **Added**     | New features                                      |
| **Changed**   | Changes in existing functionality                 |
| **Deprecated**| Soon-to-be removed features                       |
| **Removed**   | Removed features                                  |
| **Fixed**     | Bug fixes                                         |
| **Security**  | Vulnerability fixes                               |

### Automation

```bash
# Option 1: git-cliff (Rust, fast)
git cliff --output CHANGELOG.md

# Option 2: conventional-changelog (Node.js)
npx conventional-changelog -p conventionalcommits -i CHANGELOG.md -s

# Option 3: GitHub Releases (auto-generate from tags)
gh release create v1.2.0 --generate-notes
```

---

## Branch Protection Rules

Configure on GitHub / GitLab for both `main` and `develop`.

### `main` Branch

| Rule                                    | Value     |
|-----------------------------------------|-----------|
| Require pull request                    | ✅ Yes    |
| Required approvals                      | ≥ 1 (solo: 0, enable when team grows) |
| Dismiss stale reviews on new push       | ✅ Yes    |
| Require status checks to pass           | ✅ Yes (CI) |
| Require branches to be up to date       | ✅ Yes    |
| Require signed commits                  | Optional  |
| Restrict who can push                   | Release manager only |
| Allow force pushes                      | ❌ Never  |
| Allow deletions                         | ❌ Never  |

### `develop` Branch

| Rule                                    | Value     |
|-----------------------------------------|-----------|
| Require pull request                    | ✅ Yes    |
| Required approvals                      | ≥ 1 (solo: 0) |
| Require status checks to pass           | ✅ Yes (CI) |
| Allow force pushes                      | ❌ Never  |
| Allow deletions                         | ❌ Never  |

> **Solo note:** Set required approvals to 0 but still use PRs. When the first team member joins, just flip it to 1.

---

## Git Hooks

### Commit Message Validation

Save as `.githooks/commit-msg`:

```bash
#!/bin/sh

commit_msg_file="$1"
commit_msg=$(head -1 "$commit_msg_file")

# Allow merge commits
if echo "$commit_msg" | grep -qE "^Merge "; then
    exit 0
fi

# Validate conventional commit format
if ! echo "$commit_msg" | grep -qE "^(feat|fix|docs|style|refactor|perf|test|chore|ci|revert)(\(.+\))?!?: .{1,72}$"; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  ❌  INVALID COMMIT MESSAGE                             ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║                                                          ║"
    echo "║  Format:  <type>(<scope>): <subject>                     ║"
    echo "║                                                          ║"
    echo "║  Types:   feat fix docs style refactor                   ║"
    echo "║           perf test chore ci revert                      ║"
    echo "║                                                          ║"
    echo "║  Rules:   - Imperative mood (add, not added)             ║"
    echo "║           - Lowercase first letter                       ║"
    echo "║           - No period at end                              ║"
    echo "║           - Max 72 characters                             ║"
    echo "║                                                          ║"
    echo "║  Examples:                                                ║"
    echo "║    feat(auth): add biometric login                       ║"
    echo "║    fix: resolve crash on empty list                       ║"
    echo "║    chore(deps): bump Ktor to 2.3.7                      ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Your message: $commit_msg"
    echo ""
    exit 1
fi
```

### Pre-Push Protection

Save as `.githooks/pre-push`:

```bash
#!/bin/sh

# Prevent direct push to protected branches
protected_branches="main develop"
current_branch=$(git symbolic-ref HEAD | sed 's|refs/heads/||')

for branch in $protected_branches; do
    if [ "$current_branch" = "$branch" ]; then
        echo ""
        echo "❌ Direct push to '$branch' is not allowed."
        echo "   Create a branch and open a PR instead."
        echo ""
        exit 1
    fi
done
```

### Setup

```bash
# Configure git to use project hooks
git config core.hooksPath .githooks

# Make hooks executable
chmod +x .githooks/*
```

---

## CI/CD Pipeline

### GitHub Actions: CI

Save as `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [develop]
  pull_request:
    branches: [main, develop]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Validate PR commit messages
        if: github.event_name == 'pull_request'
        run: |
          git log --format='%s' ${{ github.event.pull_request.base.sha }}..${{ github.event.pull_request.head.sha }} | while read -r msg; do
            echo "$msg" | grep -qE "^Merge " && continue
            if ! echo "$msg" | grep -qE "^(feat|fix|docs|style|refactor|perf|test|chore|ci|revert)(\(.+\))?!?: .{1,72}$"; then
              echo "❌ Invalid commit message: $msg"
              exit 1
            fi
          done
          echo "✅ All commit messages valid"

  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: echo "TODO: Add your test commands"

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Build project
        run: echo "TODO: Add your build commands"
```

### GitHub Actions: Release

Save as `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    name: Create Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          draft: false
          prerelease: ${{ contains(github.ref, '-alpha') || contains(github.ref, '-beta') || contains(github.ref, '-rc') }}
```

### Pipeline Stages

| Stage         | Trigger              | Actions                                   | Required |
|---------------|----------------------|-------------------------------------------|----------|
| **Lint**      | All PRs              | Commit messages, code style, formatting   | ✅       |
| **Test**      | All PRs              | Unit tests, integration tests             | ✅       |
| **Build**     | All PRs + develop    | Compile, check for warnings               | ✅       |
| **Preview**   | PR to develop        | Deploy preview (optional)                 | Optional |
| **Release**   | Tag on main          | Build + deploy to production / store      | ✅       |
| **Notify**    | Release complete     | Slack / email notification                | Optional |

---

## CODEOWNERS

Save as `.github/CODEOWNERS`:

```
# Default owner for everything (solo)
* @your-username

# Uncomment and assign as team grows:
# /ios/           @ios-lead
# /android/       @android-lead
# /shared/        @your-username @kmp-lead
# /.github/       @your-username
# /docs/          @your-username
# build.gradle*   @your-username
# Package.swift   @ios-lead
```

---

## Project-Specific Profiles

### Personal Product (iOS / Android App)

```
Branch model:    Git Flow (main + develop + feature branches)
Versioning:      SemVer, tag every store submission
Changelog:       CHANGELOG.md, auto-generate when possible
PR requirement:  Self-review via PR, squash on branch + merge commit
CI:              Lint + Test + Build on PR, Deploy on tag
Protection:      main + develop protected, no direct push
```

### Sata (Cursor / AI workspace)

```
Branch model:    Git Flow (main + develop + feature branches)
Versioning:      SemVer tags when you publish versioned snapshots of skills or tooling
Changelog:       CHANGELOG.md optional until first tagged release
PR requirement:  Self-review via PR, squash on branch + merge commit
CI:              Add lint/validation for docs and skill manifests when ready
Protection:      main + develop protected, no direct push
Scopes:          skills, bmad, cursor, agents, docs (examples — define in commits)
```

### Open Source Library

```
Branch model:    Git Flow
Versioning:      Strict SemVer, pre-release tags for betas
Changelog:       CHANGELOG.md required, auto-generated
PR requirement:  Mandatory PR + review for external contributors
CI:              Lint + Test + Build, publish to registry on tag
Extra files:     CONTRIBUTING.md, CODE_OF_CONDUCT.md, LICENSE
Issue templates: Bug report, Feature request
PR template:     Required
```

### Client / Freelance Project

```
Branch model:    Git Flow
Versioning:      SemVer, tag every client delivery
Changelog:       CHANGELOG.md for client communication
PR requirement:  Mandatory PR, review if team > 1
CI:              Lint + Test + Build, staging on develop, production on tag
Extra:           Environment branches if needed (staging, production)
```

---

## Repo Setup Checklist

Run through this when creating any new repository:

```
Repository Setup
├── [ ] Initialize with main branch
├── [ ] Create develop branch from main
├── [ ] Set default branch = develop
├── [ ] Set up branch protection (main + develop)
│
├── Git Config
│   ├── [ ] .gitignore (gitignore.io for your stack)
│   ├── [ ] .gitattributes
│   ├── [ ] .githooks/commit-msg
│   ├── [ ] .githooks/pre-push
│   ├── [ ] Run: git config core.hooksPath .githooks
│   └── [ ] .editorconfig
│
├── Templates
│   ├── [ ] .github/PULL_REQUEST_TEMPLATE.md
│   ├── [ ] .github/ISSUE_TEMPLATE/bug_report.md
│   ├── [ ] .github/ISSUE_TEMPLATE/feature_request.md
│   └── [ ] .github/CODEOWNERS
│
├── CI/CD
│   ├── [ ] .github/workflows/ci.yml
│   └── [ ] .github/workflows/release.yml
│
├── Documentation
│   ├── [ ] README.md
│   ├── [ ] CHANGELOG.md
│   ├── [ ] LICENSE
│   └── [ ] CONTRIBUTING.md (open source)
│
└── Verify
    ├── [ ] Bad commit message → hook rejects ✅
    ├── [ ] Good commit message → hook passes ✅
    ├── [ ] Direct push to main → hook rejects ✅
    ├── [ ] Open test PR → CI runs ✅
    └── [ ] Push test tag → release workflow runs ✅
```

---

## Quick Reference

```
┌──────────────────────────────────────────────────────────────┐
│                   GIT CONVENTION CHEAT SHEET                  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  BRANCH                                                       │
│    feat/42-short-description                               │
│    fix/87-what-is-broken                                      │
│    release/1.2.0                                              │
│    hotfix/1.2.1                                               │
│                                                               │
│  COMMIT                                                       │
│    feat(scope): imperative description under 72 chars         │
│    fix(scope): what was broken and how it's fixed             │
│    chore(deps): bump library-name to x.y.z                   │
│                                                               │
│  TAG                                                          │
│    v1.2.0 (annotated, on main only, after release merge)      │
│                                                               │
│  MERGE                                                        │
│    feat/fix → develop    : squash on branch + merge commit │
│    release     → main       : merge commit (--no-ff)          │
│    hotfix      → main       : merge commit (--no-ff)          │
│    hotfix      → develop    : cherry-pick                     │
│                                                               │
│  RELEASE                                                      │
│    develop → release/x.y.z → main (tag) + back-merge develop │
│                                                               │
│  HOTFIX                                                       │
│    main → hotfix/x.y.z → main (tag) + cherry-pick develop    │
│                                                               │
│  PROTECTED                                                    │
│    main, develop — no direct push, PR only, no force push     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

*This convention is a living document. Update it as the team and project evolve.*

*Derived from `file-organization/GIT_CONVENTION.md`. Last updated: March 2026 (Sata).*