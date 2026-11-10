#!/usr/bin/env python3
"""Retain the newest two Debian versions per binary package and architecture."""
import argparse
from functools import cmp_to_key
from pathlib import Path
import subprocess


def fields(path):
    output = subprocess.check_output(
        ["dpkg-deb", "--field", str(path), "Package", "Version", "Architecture"],
        text=True,
    ).splitlines()
    if len(output) != 3:
        raise ValueError(f"Unexpected package metadata: {path}")
    return tuple(output)


def compare(a, b):
    if a == b:
        return 0
    return 1 if subprocess.run(["dpkg", "--compare-versions", a, "gt", b]).returncode == 0 else -1


def prune(pool, keep=2):
    grouped = {}
    for path in sorted(pool.glob("*.deb")):
        name, version, arch = fields(path)
        grouped.setdefault((name, arch), {}).setdefault(version, []).append(path)
    for key, versions in grouped.items():
        for version, files in versions.items():
            if len(files) != 1:
                raise ValueError(f"Duplicate binary identity {key} {version}: {files}")
        ordered = sorted(versions, key=cmp_to_key(compare), reverse=True)
        for version in ordered[keep:]:
            for path in versions[version]:
                path.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("--keep", type=int, default=2)
    args = parser.parse_args()
    if args.keep < 1:
        parser.error("--keep must be positive")
    prune(args.pool, args.keep)


if __name__ == "__main__":
    main()
