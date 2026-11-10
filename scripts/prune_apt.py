#!/usr/bin/env python3
"""Retain the newest two Debian versions per binary package and architecture."""
import argparse
from functools import cmp_to_key
from pathlib import Path
import subprocess


def fields(path):
    values = []
    for field in ("Package", "Version", "Architecture"):
        value = subprocess.check_output(
            ["dpkg-deb", "--field", str(path), field],
            text=True,
        ).strip()
        if not value or "\\n" in value:
            raise ValueError(f"Invalid {field} metadata: {path}")
        values.append(value)
    return tuple(values)


def compare(a, b):
    if a == b:
        return 0
    for relation, result in (("gt", 1), ("lt", -1)):
        completed = subprocess.run(["dpkg", "--compare-versions", a, relation, b], check=False)
        if completed.returncode == 0:
            return result
        if completed.returncode != 1:
            raise subprocess.CalledProcessError(completed.returncode, completed.args)
    raise ValueError(f"Versions could not be ordered: {a!r}, {b!r}")


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
