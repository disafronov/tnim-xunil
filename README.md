# tnim-xunil

Custom Linux Mint packages built from pinned upstream source packages and independently maintained patches.

The repository stores **no copies of upstream source trees** and does not commit generated binary packages to `main`.

## Package: gnome-calendar

`packages/gnome-calendar/package.yaml` pins the Linux Mint source package `gnome-calendar` at version `46.1-1mint2+zara` through the Linux Mint APT source repositories. The source format is `3.0 (native)`.

Three local fixes are stored as ordered unified-diff patches in `packages/gnome-calendar/patches/`:

1. `0001-enable-today-action.patch`: enable the Today action when the selected date differs from today.
2. `0002-sort-agenda-events.patch`: sort single-day agenda events chronologically.
3. `0003-diff-timeline-events.patch`: compare timeline event membership when the visible range changes.

The application order is defined by `patches/series`. The package build downloads the pinned Mint source and applies all three patches. Patch application is verified as part of the package build. The resulting Debian packages are published through GitHub Pages after successful validation.

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
index.html
tnim-xunil.asc
.github/
  workflows/
    build.yml
    publish.yml
    assign-pr.yml
```

Each immediate child of `packages/` describes one source package. `scripts/detect_changes.py` selects affected packages from changed paths, or all packages for shared script/build-workflow changes. The build workflow uses that selection logic to build affected packages.

## CI workflows

- `build.yml` runs unit tests and builds affected packages on pull requests. The build job runs inside `linuxmintd/mint22.3-amd64:latest` on an Ubuntu 24.04 GitHub Actions runner. It restores cached APT downloads, updates the build environment, installs packaging tools, and uploads the resulting `.deb` artifacts.
- `publish.yml` runs on relevant pushes to `main`, using the same Linux Mint container to rebuild packages and deploy the APT repository to GitHub Pages.
- `assign-pr.yml` assigns unassigned pull requests. The `PR_ASSIGNEE` repository variable can override the default; it is required for organization-owned repositories.
- `.github/dependabot.yml` checks GitHub Actions dependencies daily.

Each package manifest declares `source.package`, `source.version`, `source.format`, `maintainer.name`, `maintainer.email`, `build.distribution`, `build.version_suffix`, and `build.changelog_message`. The build script obtains the exact pinned source with `apt-get source` from the Linux Mint APT repositories, checks its package name, version, and source format, applies patches, updates maintainer metadata and the changelog, installs build dependencies, and builds with `dpkg-buildpackage`. It verifies the `Maintainer` field in each generated `.deb`.

## APT repository publication

`.github/workflows/publish.yml` runs on relevant pushes to `main`. It restores previously published binary packages from GitHub Pages, verifies their SHA256 checksums, and rebuilds only packages whose build inputs changed since the last published commit. During migration from the previous archive layout (without a published commit marker), it rebuilds all configured packages once. An empty APT index or HTTP 404 for `Packages.gz` means an empty archive and triggers a full build. If a binary referenced by the index returns HTTP 404, its source package is rebuilt from the current manifest. Other download errors and checksum mismatches fail publication. The archive retains the latest two Debian versions per binary package and architecture, generates a flat APT repository (`pool/`, `Packages`, `Packages.gz`, `Release`) using `dpkg-scanpackages --multiversion`, signs its Release metadata (`InRelease`, `Release.gpg`), validates signatures through APT, and deploys it to GitHub Pages. The published `index.html` redirects visitors to the [GitHub source repository](https://github.com/disafronov/tnim-xunil); APT metadata and package URLs remain directly accessible. Failed builds or validation do not replace the previously published site.

Enable **GitHub Pages → Build and deployment → Source: GitHub Actions** in repository settings.

### Install the signing key and configure APT

The repository publishes its ASCII-armored OpenPGP public key as [tnim-xunil.asc](https://disafronov.github.io/tnim-xunil/tnim-xunil.asc).

Key fingerprint:

```text
C1BB E193 86BE 4FA1 4113 DC22 970F 6970 CA2A 6BC0
```

Install the public key without converting its format:

```sh
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://disafronov.github.io/tnim-xunil/tnim-xunil.asc | \
  sudo tee /etc/apt/keyrings/tnim-xunil.asc > /dev/null
sudo chmod 0644 /etc/apt/keyrings/tnim-xunil.asc
gpg --show-keys --fingerprint /etc/apt/keyrings/tnim-xunil.asc
```

Verify that the fingerprint matches the value above before trusting the key. Then configure the source:

```text
deb [signed-by=/etc/apt/keyrings/tnim-xunil.asc] https://disafronov.github.io/tnim-xunil/ ./
```

Replace any previous `trusted=yes` entry for this repository; do not keep both entries. Run `sudo apt update` after the signed repository has been published.

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

The repository signs its APT Release metadata with a dedicated Ed25519 OpenPGP key. The publishing workflow requires the `APT_SIGNING_KEY` GitHub Actions secret (ASCII-armored private key, without a passphrase) and `APT_SIGNING_FINGERPRINT` Actions variable. The public key is committed as `tnim-xunil.asc` and published on GitHub Pages. The workflow verifies signatures and tests APT using `signed-by=` rather than `trusted=yes`. The signing key expires on 2028-11-09 and must be renewed before then. The workflow does not publish packages to `main` or create a separate promotion stage.
