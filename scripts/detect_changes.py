#!/usr/bin/env python3
"""Determine the changed package directories for a build matrix."""

import argparse
import json
from pathlib import Path, PurePosixPath


def detect(changed_paths: list[str], packages_root: Path) -> list[str]:
    available = (
        {p.name for p in packages_root.iterdir() if p.is_dir() and not p.is_symlink()}
        if packages_root.is_dir()
        else set()
    )
    selected = set()
    rebuild_all = False
    for raw in changed_paths:
        parts = PurePosixPath(raw).parts
        if len(parts) >= 3 and parts[0] == "packages" and parts[1] in available:
            selected.add(parts[1])
        elif parts and (parts[0] == "scripts" or raw in (".github/workflows/build.yml", ".github/workflows/publish.yml")):
            rebuild_all = True
    return sorted(available if rebuild_all else selected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages-root", type=Path, default=Path("packages"))
    parser.add_argument("--changed-files", type=Path, required=True)
    args = parser.parse_args()
    changed = args.changed_files.read_text(encoding="utf-8").splitlines()
    print(json.dumps({"package": detect(changed, args.packages_root)}, separators=(",", ":")))


if __name__ == "__main__":
    main()
