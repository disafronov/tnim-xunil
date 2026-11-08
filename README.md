# tnim-xunil

Custom Linux Mint packages built from pinned upstream source packages and independently maintained patches.

The repository stores **no copies of upstream source trees** and does not commit generated binary packages to `main`.

## Package: gnome-calendar

`packages/gnome-calendar/package.yaml` pins the Linux Mint source package `gnome-calendar` at version `46.1-1mint2+zara` using its published `.dsc` file. The source format is `3.0 (native)`.

Three local fixes are stored as ordered unified-diff patches in `packages/gnome-calendar/patches/`:

1. `0001-enable-today-action.patch`: enable the Today action when the selected date differs from today.
2. `0002-sort-agenda-events.patch`: sort single-day agenda events chronologically.
3. `0003-diff-timeline-events.patch`: compare timeline event membership when the visible range changes.

The application order is defined by `patches/series`. GitHub Actions has successfully downloaded the pinned Mint source and applied all three patches. Patch application was verified in CI. The user also successfully downloaded the first built artifact and opened it for installation; runtime behavior is not yet established.

## Repository layout

```text
packages/
  gnome-calendar/
    package.yaml
    patches/
      series
      0001-enable-today-action.patch
      0002-sort-agenda-events.patch
      0003-diff-timeline-events.patch
scripts/
  detect_changes.py
.github/
  workflows/
    verify-gnome-calendar-patches.yml
    build.yml
    assign-pr.yml
```

Each immediate child of `packages/` describes one source package. `scripts/detect_changes.py` selects affected packages from changed paths, or all packages for shared script/build-workflow changes. The build workflow does not yet use that selection logic.

## CI workflows

- `verify-gnome-calendar-patches.yml` runs on relevant pull requests and can be dispatched manually. It downloads the pinned Linux Mint source and applies the ordered patches. Its first run passed.
- `build.yml` runs on relevant pull requests and can be dispatched manually. It downloads and patches the source, adds a local Debian changelog revision, installs build dependencies, attempts a binary build with `dpkg-buildpackage`, and uploads any generated `.deb` files as GitHub Actions artifacts. The first build produced a downloadable artifact. The current revision additionally checks the resulting Debian `Maintainer` field.
- `assign-pr.yml` assigns unassigned pull requests. The `PR_ASSIGNEE` repository variable can override the default; it is required for organization-owned repositories.
- `.github/dependabot.yml` checks GitHub Actions dependencies daily.

The derivative package sets `Maintainer: Dmitrii Safronov <dhameoelin@gmail.com>` in `debian/control` before building and checks that field in the generated `.deb`. The original Debian/Ubuntu maintainer attribution remains available in upstream metadata. The local changelog entry also uses this maintainer identity.\n\nSource retrieval currently uses `dget -u -x`: archive checksums are checked against the `.dsc`, but OpenPGP signature verification is skipped. The build runs on an Ubuntu 24.04 runner; Mint-specific build dependencies may need additional handling.

## Planned publication

The intended pipeline will detect affected packages, build their Debian binaries, and automatically publish packages and APT metadata through GitHub Pages after merging. Shared build-tool changes may trigger rebuilding all packages. No separate manual promotion or tagging stage is planned.

**Not implemented yet:** automatic package selection in the build workflow and APT repository publication through GitHub Pages.
