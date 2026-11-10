#!/usr/bin/env python3
"""Download and verify the previously published flat APT repository."""
import argparse
import gzip
import hashlib
from pathlib import Path, PurePosixPath
import urllib.error
import urllib.parse
import urllib.request


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status}: {url}")
        return response.read()


def records(index):
    for block in index.split("\n\n"):
        if not block.strip():
            continue
        fields = {}
        for line in block.splitlines():
            if line.startswith(" ") or ": " not in line:
                continue
            key, value = line.split(": ", 1)
            fields[key] = value
        yield fields


def restore(base_url, destination, missing_sources=None):
    base_url = base_url.rstrip("/") + "/"
    destination.mkdir(parents=True, exist_ok=True)
    # Missing index means an empty archive; other download errors remain fatal.
    try:
        raw = fetch(urllib.parse.urljoin(base_url, "Packages.gz"))
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        index = ""
    else:
        index = gzip.decompress(raw).decode("utf-8")
    seen = set()
    missing = set()
    for item in records(index):
        name = item["Filename"]
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or path.parts[0] != "pool":
            raise ValueError(f"Unsafe package path: {name}")
        if name in seen:
            raise ValueError(f"Duplicate package filename: {name}")
        seen.add(name)
        try:
            payload = fetch(urllib.parse.urljoin(base_url, name))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            # A missing binary is rebuilt from the current source manifest.
            source = item.get("Source", item["Package"]).split(" (", 1)[0]
            missing.add(source)
            continue
        if len(payload) != int(item["Size"]):
            raise ValueError(f"Size mismatch: {name}")
        if hashlib.sha256(payload).hexdigest() != item["SHA256"]:
            raise ValueError(f"SHA256 mismatch: {name}")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    if missing_sources is not None:
        missing_sources.write_text("".join(f"{source}\n" for source in sorted(missing)))
    # The state file is optional only during migration from the old layout.
    try:
        state = fetch(urllib.parse.urljoin(base_url, ".published-commit")).decode().strip()
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        state = ""
    if state and (len(state) != 40 or any(c not in "0123456789abcdef" for c in state)):
        raise ValueError("Invalid published commit SHA")
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--missing-sources", type=Path)
    args = parser.parse_args()
    print(restore(args.url, args.directory, args.missing_sources))


if __name__ == "__main__":
    main()
