# Patents Workflow Repository Design

Date: 2026-06-06

## Goal

Create a local development repository for the patents workflow skill suite. The repository is the source for collaboration, checks, releases, and later GitHub publication. Codex still discovers skills from `C:\Users\spade k\.codex\skills`, so the repository must provide a sync path instead of becoming the live skill root.

## Repository Identity

Use a stable repository name:

```text
C:\Users\spade k\patents-workflow
```

The suite version starts at `1.6.0`. Future releases move from `1.6.0` to `1.7.0`, `2.0.0`, and so on in the same repository. Do not create versioned repositories such as `patents-workflow-v1.7` for normal iteration.

Version state lives in:

- `VERSION`
- `manifest.json`
- `CHANGELOG.md`
- git tags such as `v1.6.0` and `v1.7.0`
- GitHub Releases after publication

## Skill Scope

The initial suite includes 15 skills copied from `C:\Users\spade k\.codex\skills`.

Primary patent workflow skills:

- `cn-patent-repo-scout`
- `cn-patent-mainline-analysis`
- `cn-patent-prior-art-search`
- `cn-patent-disclosure-draft`
- `cn-patent-disclosure-review`
- `cn-patent-formal-drafting`
- `cn-patent-attorney-review`
- `cn-patent-docx-export`
- `cn-patent-project-drafting`

Vendored supporting skills:

- `seaborn`
- `scientific-visualization`
- `scientific-schematics`
- `matplotlib`
- `markdown-mermaid-writing`
- `generate-image`

The supporting skills are vendored dependencies. They are copied, checked, and synchronized with the suite, but are not the default target for functional changes unless a later task explicitly scopes that work.

## Directory Layout

```text
patents-workflow/
  README.md
  LICENSE
  CONTRIBUTING.md
  CHANGELOG.md
  VERSION
  manifest.json
  .gitignore
  docs/
    development.md
    superpowers/
      specs/
        2026-06-06-patents-workflow-repo-design.md
  scripts/
    sync-to-codex-skills.ps1
    check-release.ps1
  skills/
    cn-patent-repo-scout/
    cn-patent-mainline-analysis/
    cn-patent-prior-art-search/
    cn-patent-disclosure-draft/
    cn-patent-disclosure-review/
    cn-patent-formal-drafting/
    cn-patent-attorney-review/
    cn-patent-docx-export/
    cn-patent-project-drafting/
    seaborn/
    scientific-visualization/
    scientific-schematics/
    matplotlib/
    markdown-mermaid-writing/
    generate-image/
```

Each skill remains a direct child of `skills/` and must contain its own `SKILL.md`. When synchronized, each skill is copied to `C:\Users\spade k\.codex\skills\<skill-name>`, preserving Codex discovery behavior.

## Sync Strategy

`scripts/sync-to-codex-skills.ps1` synchronizes from the repository to the live Codex skill directory.

Default behavior is dry-run. It reports what would be copied, removed, or overwritten. A separate explicit flag performs writes.

Expected behavior:

- read the skill list from `manifest.json`
- copy only declared skill directories
- exclude cache and generated files such as `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, and `.ruff_cache/`
- refuse to run if source skill directories do not contain `SKILL.md`
- avoid touching non-suite skills in `C:\Users\spade k\.codex\skills`

## Release Check Strategy

`scripts/check-release.ps1` validates the repository before collaboration or publication.

Required checks:

- every manifest skill exists under `skills/`
- every skill has `SKILL.md`
- every `SKILL.md` frontmatter includes `name` and `description`
- no `__pycache__/` or `*.pyc` files are present
- no obvious secret patterns are present
- README skill list matches `manifest.json`
- `VERSION` matches `manifest.json.version`

The first implementation may keep the checks simple and deterministic. More checks can be added after the repository is stable.

## Publication Path

Stage 1 is local repository cleanup only.

Stage 2 can push the repository to a private GitHub repository named `patents-workflow` and invite collaborators.

Stage 3 can prepare for public open source by adding or confirming:

- license choice
- patent/legal disclaimer
- contribution policy
- issue and pull request templates
- release checklist
- CI checks
- security policy if needed

## Non-Goals

This setup does not redesign the patent workflow itself. It does not merge all skills into one parent skill. It does not make `patents-workflow` the live Codex skill root. It does not change vendored supporting skill behavior by default.

## Approval Criteria

The first implementation is complete when:

- the local git repository exists
- the 15 declared skills are copied under `skills/` without cache artifacts
- repository governance files exist
- sync and release-check scripts exist
- release checks pass
- the live Codex skill discovery layout remains compatible
