#!/usr/bin/env python3
"""Check required published files before skipping APT repository deployment."""

import argparse
import subprocess
import tempfile
import urllib.error
import urllib.parse
from pathlib import Path

from scripts.restore_apt import fetch


def check(base_url: str, public_key: Path, index_html: Path) -> bool:
    base_url = base_url.rstrip("/") + "/"
    required = ("Release", "Release.gpg", "InRelease", "tnim-xunil.asc", "index.html")
    published = {}
    for name in required:
        try:
            published[name] = fetch(urllib.parse.urljoin(base_url, name))
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return False
            raise

    if published["tnim-xunil.asc"] != public_key.read_bytes():
        return False
    if published["index.html"] != index_html.read_bytes():
        return False

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        keyring = root / "keyring.gpg"
        subprocess.run(
            ["gpg", "--batch", "--yes", "--dearmor", "--output", str(keyring), str(public_key)],
            check=True,
        )
        for name in ("Release", "Release.gpg", "InRelease"):
            (root / name).write_bytes(published[name])
        signed_content = root / "signed-content"
        subprocess.run(
            ["gpgv", "--keyring", str(keyring), "--output", str(signed_content), str(root / "InRelease")],
            check=True,
        )
        subprocess.run(
            ["gpgv", "--keyring", str(keyring), str(root / "Release.gpg"), str(root / "Release")],
            check=True,
        )
        if signed_content.read_bytes() != published["Release"]:
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--index-html", type=Path, required=True)
    args = parser.parse_args()
    if not check(args.url, args.public_key, args.index_html):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
