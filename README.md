# tnim-xunil

Independently maintained patches for Linux Mint packages, built and distributed through a signed APT repository.

This project rebuilds pinned Linux Mint source packages with independently maintained fixes for upstream issues. It does not store copies of upstream source trees or generated binary packages in Git; published binaries are retained in the APT archive.

**Supported distribution:** Linux Mint 22.3 (Zena), amd64.

## Available packages

| Package | Fixes |
| --- | --- |
| `gnome-calendar` | Today action availability, chronological agenda ordering, and timeline updates when the visible range changes. |

The `gnome-calendar` package currently uses Linux Mint source version `46.1-1mint2+zara` (`3.0 (native)`). Its ordered patches are in [`packages/gnome-calendar/patches/`](packages/gnome-calendar/patches/):

1. `0001-enable-today-action.patch`: enable Today when the selected date differs from today.
2. `0002-sort-agenda-events.patch`: sort single-day agenda events chronologically.
3. `0003-diff-timeline-events.patch`: compare timeline event membership when the visible range changes.

The patch order is defined by `patches/series`.

## Installation

This is a third-party APT repository. Review its packages and signing key before trusting them. APT signatures authenticate repository metadata and package integrity; they do not guarantee the correctness or safety of patches.

### Signing key

The repository publishes its ASCII-armored OpenPGP public key as [`tnim-xunil.asc`](https://disafronov.github.io/tnim-xunil/tnim-xunil.asc).

Install the key without converting its format:

```sh
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://disafronov.github.io/tnim-xunil/tnim-xunil.asc | \
  sudo tee /etc/apt/keyrings/tnim-xunil.asc > /dev/null
sudo chmod 0644 /etc/apt/keyrings/tnim-xunil.asc
```

### APT source

```sh
sudo tee /etc/apt/sources.list.d/tnim-xunil.list > /dev/null <<'EOF'
deb [signed-by=/etc/apt/keyrings/tnim-xunil.asc] https://disafronov.github.io/tnim-xunil/ ./
EOF
```

Replace any older `trusted=yes` entry for this repository rather than keeping both.

### Package priority

Choose **one** of the following configurations. Both select packages by the APT Release `Origin: tnim-xunil` field, rather than by hostname.

**All packages:** prefer every package published by this repository.

```sh
sudo tee /etc/apt/preferences.d/tnim-xunil.pref > /dev/null <<'EOF'
Package: *
Pin: release o=tnim-xunil
Pin-Priority: 1001
EOF
```

**Individual packages:** prefer only `gnome-calendar` from this repository.

```sh
sudo tee /etc/apt/preferences.d/tnim-xunil.pref > /dev/null <<'EOF'
Package: gnome-calendar
Pin: release o=tnim-xunil
Pin-Priority: 1001
EOF
```

To target additional packages, add their names to the `Package:` field separated by spaces, or use separate preference records. Both examples replace the same preferences file; they are alternatives, not cumulative steps.

Priority `1001` allows APT to select an older version from this repository over a newer version from an ordinary repository (a downgrade). Review proposed package changes before proceeding. Pinning controls candidate selection, not which packages a repository is allowed to publish.

### Update and install

```sh
sudo apt update
apt policy gnome-calendar
sudo apt install gnome-calendar
```

Inspect the candidate version and origin reported by `apt policy` before installing.

## How it works

### Source packages and patches

Each immediate child of `packages/` defines one source package. Its `package.yaml` pins the upstream source package, version and source format, and specifies maintainer and build metadata. The build downloads that exact source using `apt-get source` from Linux Mint APT repositories, checks its identity and format, applies the ordered patch series, updates the changelog and maintainer metadata, and builds with `dpkg-buildpackage`. Patch application and the generated Debian package's `Maintainer` field are verified.

### Build and publication

Pull requests run tests and build affected packages. The build uses `linuxmintd/mint22.3-amd64:latest` on an Ubuntu 24.04 GitHub Actions runner. Changes to shared build scripts or workflows can trigger builds of all packages.

On relevant pushes to `main`, publication restores existing packages from the published APT archive, verifies SHA256 checksums, and rebuilds only packages affected since the last published commit. If a referenced binary is missing, its source package is rebuilt. Download failures other than the documented empty-archive/missing-binary cases and checksum mismatches abort publication.

The archive retains the latest **two Debian versions per binary package and architecture**. It generates a flat APT index (`pool/`, `Packages`, `Packages.gz`, `Release`) with `dpkg-scanpackages --multiversion`, signs `InRelease` and `Release.gpg`, validates signatures and APT access, and deploys through GitHub Pages. Failed builds or validation do not replace the previously published site.

Retaining binaries means previously published packages remain available even if the pinned source is subsequently removed upstream; rebuilding that source still requires it to be available.

### Repository signing

The dedicated Ed25519 OpenPGP key signs APT Release metadata. The workflow verifies signatures and checks APT access using `signed-by=`, not `trusted=yes`. The signing key expires on **2028-11-09** and must be renewed before then.

The archive declares `Origin: tnim-xunil`, `Suite`/`Codename: zena`, and `Version: 22.3`. Derivative package versions use the `+disafronovYYYYMMDDHHMMSS` UTC suffix.

## Repository structure

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

## Maintenance

### Package manifests

Each package manifest declares `source.package`, `source.version`, `source.format`, `maintainer.name`, `maintainer.email`, `build.distribution`, `build.version_suffix`, and `build.changelog_message`. To add another package, create its directory under `packages/`, define its manifest and ordered patch series, and let the build workflow validate it.

### GitHub Actions

- `build.yml` runs tests and builds affected packages on pull requests, restoring cached APT downloads and uploading `.deb` artifacts.
- `publish.yml` publishes the signed APT archive on relevant pushes to `main`. It tracks the last published commit for incremental rebuilds.
- `assign-pr.yml` assigns unassigned pull requests; `PR_ASSIGNEE` can override its default and is required for organization-owned repositories.
- `.github/dependabot.yml` checks GitHub Actions dependencies daily.

Configure **GitHub Pages → Build and deployment → Source: GitHub Actions**.

Publishing requires the `APT_SIGNING_KEY` GitHub Actions secret (ASCII-armored, unencrypted private key). The workflow derives the signing fingerprint from `tnim-xunil.asc` and checks that the imported private key matches it. The public key is committed as `tnim-xunil.asc` and published alongside the archive. The workflow does not commit binaries to `main` or use a separate promotion stage.

The published `index.html` redirects visitors to the [source repository](https://github.com/disafronov/tnim-xunil/); APT metadata and package URLs remain directly accessible.
