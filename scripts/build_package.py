#!/usr/bin/env python3
"""Build a patched Debian package from its declarative manifest."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import shutil
import tempfile

import yaml


def run(*args, cwd=None, env=None):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    package_dir = args.package_dir.resolve()
    output_dir = args.output_dir.resolve()
    manifest = yaml.safe_load((package_dir / "package.yaml").read_text())
    source = manifest["source"]
    maintainer = manifest["maintainer"]
    build = manifest["build"]
    identity = f'{maintainer["name"]} <{maintainer["email"]}>'
    env = dict(os.environ, DEBFULLNAME=maintainer["name"], DEBEMAIL=maintainer["email"])
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="deb-build-") as temp:
        root = Path(temp)
        run("dget", "-u", "-x", source["dsc"], cwd=root)
        trees = [p for p in root.iterdir() if p.is_dir() and (p / "debian/control").is_file()]
        if len(trees) != 1:
            raise RuntimeError(f"Expected one extracted Debian source tree, got {trees}")
        tree = trees[0]
        actual_format = subprocess.check_output(
            ["dpkg-source", "--print-format", str(tree)], text=True
        ).strip()
        if actual_format != source["format"]:
            raise RuntimeError(f"Source format mismatch: {actual_format}")
        changelog = subprocess.check_output(
            ["dpkg-parsechangelog", "-S", "Version"], cwd=tree, text=True
        ).strip()
        if changelog != source["version"]:
            raise RuntimeError(f"Source version mismatch: {changelog}")
        actual_package = subprocess.check_output(
            ["dpkg-parsechangelog", "-S", "Source"], cwd=tree, text=True
        ).strip()
        if actual_package != source["package"]:
            raise RuntimeError(f"Source package mismatch: {actual_package}")
        control = tree / "debian/control"
        text = control.read_text()
        matches = re.findall(r"^Maintainer: .+$", text, flags=re.MULTILINE)
        if len(matches) != 1:
            raise RuntimeError(f"Expected one Maintainer field, got {matches}")
        control.write_text(text.replace(matches[0], f"Maintainer: {identity}", 1))

        for line in (package_dir / "patches/series").read_text().splitlines():
            patch = line.strip()
            if not patch or patch.startswith("#"):
                continue
            with (package_dir / "patches" / patch).open("rb") as stream:
                subprocess.run(
                    ["patch", "--batch", "--forward", "--fuzz=0", "-p1"],
                    stdin=stream, cwd=tree, check=True,
                )

        run(
            "dch", "--local", build["version_suffix"],
            "--distribution", build["distribution"], "--force-distribution",
            build["changelog_message"], cwd=tree, env=env,
        )
        run(
            "sudo", "mk-build-deps", "--install", "--remove",
            "--tool", "apt-get -y --no-install-recommends", "debian/control",
            cwd=tree,
        )
        run("dpkg-buildpackage", "--build=binary", "--no-sign", cwd=tree, env=env)
        packages = sorted(root.glob("*.deb"))
        if not packages:
            raise RuntimeError("No binary .deb files produced")
        for package in packages:
            actual = subprocess.check_output(
                ["dpkg-deb", "--field", str(package), "Maintainer"], text=True
            ).strip()
            if actual != identity:
                raise RuntimeError(f"{package.name}: unexpected Maintainer: {actual}")
            destination = output_dir / package.name
            shutil.copy2(package, destination)
            print(f"Built {destination} (Maintainer: {actual})", flush=True)


if __name__ == "__main__":
    main()
