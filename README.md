# tnim-xunil

Custom Linux Mint packages built from pinned upstream source packages and independently maintained patches.

The repository stores **no copies of upstream source trees** and does not commit generated binary packages to `main`.

## Package: gnome-calendar

`packages/gnome-calendar/package.yaml` pins the Linux Mint source package `gnome-calendar` at version `46.1-1mint2+zara` using its published `.dsc` file. The source format is `3.0 (native)`.

Three local fixes are stored as ordered unified-diff patches in `packages/gnome-calendar/patches/`:

1. `0001-enable-today-action.patch`: enable the Today action when the selected date differs from today.
2. `0002-sort-agenda-events.patch`: sort single-day agenda events chronologically.
3. `0003-diff-timeline-events.patch`: compare timeline event membership when the visible range changes.

The application order is defined by `patches/series`. The package build downloads the pinned Mint source and applies all three patches. Patch application is verified as part of the package build. The user also successfully downloaded the first built artifact and opened it for installation; runtime behavior is not yet established.

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
  build_package.py
  restore_apt.py
  prune_apt.py
.github/
  workflows/
    build.yml
    publish.yml
    assign-pr.yml
```

Each immediate child of `packages/` describes one source package. `scripts/detect_changes.py` selects affected packages from changed paths, or all packages for shared script/build-workflow changes. The build workflow uses that selection logic to generate a per-package build matrix.

## CI workflows

- `build.yml` runs on pull requests changing package files, shared scripts, or the build workflow; A detection job compares the pull request head against its base and passes the selected package names to a matrix. Each matrix job invokes `scripts/build_package.py` with its package directory. The script reads `package.yaml`, downloads and validates the pinned source, applies the patch series, sets derivative maintainer metadata, creates a local Debian changelog revision, installs build dependencies, builds with `dpkg-buildpackage`, and verifies the resulting `.deb` metadata before upload. The first build produced a downloadable artifact. The current revision additionally checks the resulting Debian `Maintainer` field.
- `assign-pr.yml` assigns unassigned pull requests. The `PR_ASSIGNEE` repository variable can override the default; it is required for organization-owned repositories.
- `.github/dependabot.yml` checks GitHub Actions dependencies daily.

The package manifest declares `source.package`, `source.version`, `source.dsc`, `source.format`, `maintainer.name`, `maintainer.email`, `build.distribution`, `build.version_suffix`, and `build.changelog_message`. The build script uses the manifest for source selection, version/format checks, maintainer attribution, and changelog generation. The derivative package sets `Maintainer: Dmitrii Safronov <dhameoelin@gmail.com>` in `debian/control` before building and checks that field in the generated `.deb`. The original Debian/Ubuntu maintainer attribution remains available in upstream metadata. The local changelog entry also uses this maintainer identity.

Source retrieval currently uses `dget -u -x`: archive checksums are checked against the `.dsc`, but OpenPGP signature verification is skipped. The build runs on an Ubuntu 24.04 runner; Mint-specific build dependencies may need additional handling.

## APT repository publication

`.github/workflows/publish.yml` runs on relevant pushes to `main`. It restores previously published binary packages from GitHub Pages, verifies their SHA256 checksums, and rebuilds only packages whose build inputs changed since the last published commit. During migration from the previous archive layout (without a published commit marker), it rebuilds all configured packages once. An empty APT index or HTTP 404 for `Packages.gz` means an empty archive and triggers a full build. If a binary referenced by the index returns HTTP 404, its source package is rebuilt from the current manifest. Other download errors and checksum mismatches fail publication. The archive retains the latest two Debian versions per binary package and architecture, generates a flat APT repository (`pool/`, `Packages`, `Packages.gz`, `Release`) using `dpkg-scanpackages --multiversion`, validates it through APT, and deploys it to GitHub Pages. Failed builds or validation do not replace the previously published site.

Enable **GitHub Pages → Build and deployment → Source: GitHub Actions** in repository settings. Once deployed, configure APT with:

```text
deb [trusted=yes] https://disafronov.github.io/tnim-xunil/ ./
```

To prioritize all packages from this repository, install an APT preferences rule:

```sh
sudo tee /etc/apt/preferences.d/tnim-xunil.pref > /dev/null <<'EOF'
Package: *
Pin: release o=tnim-xunil
Pin-Priority: 1001
EOF

sudo apt update
apt policy gnome-calendar
```

The rule applies to all packages in APT repositories declaring `Origin: tnim-xunil`
in their `Release` metadata, not to every repository on the same host. A priority
above 1000 also permits downgrades, so review proposed package changes.

The published APT `Release` metadata identifies the archive as `tnim-xunil`
(`Origin`), labels it `Dmitrii Safronov's Patched Packages`, and targets
Linux Mint 22.3 Zena (`Suite`/`Codename: zena`, `Version: 22.3`).
Its description is `Personal fixes for upstream bugs and annoyances`.
Derivative package versions use `+disafronovYYYYMMDDHHMMSS` (UTC).

The repository is **unsigned**: `trusted=yes` explicitly disables APT signature verification for this source. Use it only if you trust the repository owner and GitHub Pages delivery. Signing and key distribution are not implemented. The URL is the expected GitHub Pages project URL, not a verified live deployment. The workflow does not publish packages to `main` or create a separate promotion stage.
