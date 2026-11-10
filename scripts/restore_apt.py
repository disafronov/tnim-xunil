#!/usr/bin/env python3
"""Download and verify the previously published flat APT repository."""
import argparse
import time
import gzip
import hashlib
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
import urllib.error
import urllib.parse
import urllib.request


def fetch(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"Unexpected HTTP status {response.status}: {url}")
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def verify_index(index, inrelease, public_key):
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        keyring = directory / "keyring.gpg"
        signed = directory / "InRelease"
        subprocess.run(
            ["gpg", "--batch", "--yes", "--dearmor", "--output", str(keyring), str(public_key)],
            check=True,
        )
        signed.write_bytes(inrelease)
        subprocess.run(["gpgv", "--keyring", str(keyring), str(signed)], check=True)

    # Read the cleartext-signed Release fields, including the SHA256 table.
    release = inrelease.split(b"\n\n", 1)[1].split(b"\n-----BEGIN PGP SIGNATURE-----", 1)[0]
    lines = release.decode("utf-8").splitlines()
    digest = hashlib.sha256(index).hexdigest()
    matches = []
    in_sha256 = False
    for line in lines:
        if line == "SHA256:":
            in_sha256 = True
            continue
        if in_sha256 and not line.startswith(" "):
            in_sha256 = False
        if in_sha256:
            parts = line.split()
            if len(parts) == 3 and parts[2] == "Packages.gz":
                matches.append((parts[0], parts[1]))
    if len(matches) != 1 or matches[0] != (digest, str(len(index))):
        raise ValueError("Packages.gz does not match signed Release SHA256 metadata")


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


def restore(base_url, destination, missing_sources=None, public_key=None):
    base_url = base_url.rstrip("/") + "/"
    destination.mkdir(parents=True, exist_ok=True)
    # Missing index means an empty archive; other download errors remain fatal.
    index_missing = False
    try:
        raw = fetch(urllib.parse.urljoin(base_url, "Packages.gz"))
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        index = ""
        index_missing = True
    else:
        if public_key is None:
            raise ValueError("Public signing key required to restore an existing archive")
        verify_index(raw, fetch(urllib.parse.urljoin(base_url, "InRelease")), public_key)
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
    # No index means no usable published packages, regardless of any stale marker.
    if index_missing:
        if missing_sources is not None:
            missing_sources.write_text("")
        return ""
    # The state file is optional only during migration from the old layout.
    try:
        state = fetch(urllib.parse.urljoin(base_url, "published-commit")).decode().strip()
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
    parser.add_argument("--public-key", type=Path, default=Path("tnim-xunil.asc"))
    args = parser.parse_args()
    print(restore(args.url, args.directory, args.missing_sources, args.public_key))


if __name__ == "__main__":
    main()
