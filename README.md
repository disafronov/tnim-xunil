# tnim-xunil

Custom Linux Mint packages built from pinned upstream source packages and independently maintained patches.

The repository stores **no copies of upstream source trees** and does not commit generated binary packages to `main`.

## Approach

Patches are developed and tested against Linux Mint sources separately before being added here.

The planned GitHub Actions pipeline will:

1. Detect changed package directories and build only affected packages.
2. Download a pinned upstream source package and verify its integrity.
3. Apply ordered patches and build Debian binary packages.
4. Automatically publish the resulting packages and updated APT metadata via GitHub Pages.

Shared build-tool changes may trigger rebuilding all packages. No separate manual promotion stage is planned.

## Planned layout

```text
packages/
  gnome-calendar/
    package.yaml
    patches/
.github/
  workflows/
```

Each immediate child of `packages/` describes one source package. This boundary keeps changed-package detection straightforward.

## Existing repository automation

This repository was created from `basic-template` and currently includes:

- `.github/workflows/assign-pr.yml`: assigns unassigned pull requests to the maintainer. The `PR_ASSIGNEE` repository variable can override the default; it is required for organization-owned repositories.
- `.github/dependabot.yml`: checks GitHub Actions dependencies daily.

## Status

The package definitions, build pipeline, and APT repository publication are **not yet implemented**.
