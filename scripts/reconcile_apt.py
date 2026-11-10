#!/usr/bin/env python3
"""Remove published binaries whose source packages are no longer maintained."""

import argparse
from pathlib import Path
import subprocess

import yaml


def maintained_sources(packages_root: Path) -> set[str]:
    sources = set()
    for manifest in sorted(packages_root.glob("*/package.yaml")):
        source = yaml.safe_load(manifest.read_text())["source"]["package"]
        if source in sources:
            raise ValueError(f"Duplicate maintained source package: {source}")
        sources.add(source)
    return sources


def binary_source(path: Path) -> str:
    source = subprocess.check_output(
        ["dpkg-deb", "--field", str(path), "Source"], text=True
    ).strip()
    if source:
        return source.split(" (", 1)[0]
    return subprocess.check_output(
        ["dpkg-deb", "--field", str(path), "Package"], text=True
    ).strip()


def reconcile(pool: Path, packages_root: Path) -> list[Path]:
    maintained = maintained_sources(packages_root)
    removed = []
    for deb in sorted(pool.glob("*.deb")):
        if binary_source(deb) not in maintained:
            deb.unlink()
            removed.append(deb)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("--packages-root", type=Path, default=Path("packages"))
    args = parser.parse_args()
    for path in reconcile(args.pool, args.packages_root):
        print(path)


if __name__ == "__main__":
    main()
