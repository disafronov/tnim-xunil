#!/usr/bin/env python3
"""Check whether the Linux Mint source package has a newer published version."""
import argparse
from pathlib import Path
import re
import subprocess

import yaml


def newer(candidate, current):
    return subprocess.run(
        ["dpkg", "--compare-versions", candidate, "gt", current],
        check=False,
    ).returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    manifest = args.manifest
    data = yaml.safe_load(manifest.read_text())
    source = data["source"]
    package, current = source["package"], source["version"]

    # Use the very same APT source indices as 'apt-get source' in the builder.
    output = subprocess.check_output(["apt-cache", "showsrc", package], text=True)
    versions = re.findall(r"^Version:\s*(\S+)\s*$", output, re.MULTILINE)
    # Mint revisions for this distribution are distinguished from Ubuntu
    # versions by the distribution suffix already pinned in the manifest.
    distro = data["build"]["distribution"]
    suffix = f"+{distro}"
    candidates = [v for v in versions if suffix in v]
    if not candidates:
        raise RuntimeError(f"No {package} source versions for {distro} in APT indices")

    latest = candidates[0]
    for version in candidates[1:]:
        if newer(version, latest):
            latest = version

    if not newer(latest, current):
        print(f"{package}: no update ({current}; latest: {latest})")
        return

    original = manifest.read_text()
    pattern = r'(?m)^(\s*version:\s*)["\']?' + re.escape(current) + r'["\']?(\s*)$'
    updated, count = re.subn(pattern, lambda m: f'{m.group(1)}"{latest}"{m.group(2)}', original)
    if count != 1:
        raise RuntimeError("Cannot uniquely locate the pinned source version")
    manifest.write_text(updated)
    print(f"{package}: {current} -> {latest}")


if __name__ == "__main__":
    main()
